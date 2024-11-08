from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from .filters import ProductFilter
from .logic import (add_product_to_cart, get_or_create_user_cart,
                    remove_product_from_cart, update_cart_item_quantity)
from .models import Cart, Category, Product
from .serializers import (CartSerializer, CategoriesSerializer,
                          CategoryFilterSerializer, DestroyCartSerializer,
                          POSTCartSerializer, ProductSerializer)
from .tasks import process_order
from .utils import get_coordinates


class ProductViewSet(ReadOnlyModelViewSet):
    """
    Вьюсет для просмотра списка товаров и получения информации о товаре.
    Позволяет фильтровать и сортировать товары по цене.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter
    ordering_fields = ["price"]
    ordering = ["price"]

    @swagger_auto_schema(
        operation_id="list_products",
        operation_description="Получение списка товаров с возможностью фильтрации и сортировки по цене",
        manual_parameters=[
            openapi.Parameter(
                "ordering",
                openapi.IN_QUERY,
                description="Поле для сортировки",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={200: ProductSerializer(many=True), 400: "Bad request"},
    )
    def list(self, request, *args, **kwargs):
        """
        Получение списка товаров с возможностью
        фильтрации по цене и сортировке.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="retrieve_product",
        operation_description="Получение детальной информации о товаре",
        responses={200: ProductSerializer, 404: "Product not found"},
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Получение детальной информации о товаре.
        """
        return super().retrieve(request, *args, **kwargs)


class ProductsAPIView(APIView):
    """
    API для получения товаров по категории. Принимает ID категории
    и возвращает список товаров, относящихся к этой категории.
    """

    @swagger_auto_schema(
        operation_id="products_category",
        request_body=CategoryFilterSerializer,
        responses={200: ProductSerializer(many=True), 400: "Bad Request"},
        operation_description="Получение списка товаров по категории",
    )
    def post(self, request):
        """
        POST /products — получение товаров по категории.
        Ожидает ID категории в данных запроса.
        """

        serializer = CategoryFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category_id = serializer.validated_data.get("category")

        queryset = (
            Product.objects.filter(category_id=category_id)
            if category_id
            else Product.objects.all()
        )

        product_serializer = ProductSerializer(queryset, many=True)
        return Response(product_serializer.data, status=status.HTTP_200_OK)


class CategoryViewSet(ReadOnlyModelViewSet):
    """
    Вьюсет для получения информации о категориях товаров.
    Позволяет просматривать список категорий и подкатегорий.
    """

    queryset = Category.objects.all()
    serializer_class = CategoriesSerializer

    @swagger_auto_schema(
        operation_id="list_categories",
        operation_description="Получение списка категорий, включая подкатегории",
        responses={200: CategoriesSerializer(many=True), 400: "Bad request"},
    )
    def list(self, request, *args, **kwargs):
        """
        Получение списка категорий с подкатегориями.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="retrieve_category",
        operation_description="Получение детальной информации о категории, включая её подкатегории",
        responses={200: CategoriesSerializer, 404: "Category not found"},
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Получение детальной информации о категории.
        """
        return super().retrieve(request, *args, **kwargs)


class CartViewSet(GenericViewSet):
    """
    Вьюсет для управления корзиной пользователя.
    Позволяет добавлять, изменять, удалять товары из корзины,
    а также просматривать её.
    """

    serializer_class = CartSerializer

    def get_serializer_class(self):
        """
        Возвращает соответствующий сериализатор в зависимости от действия.
        """
        if self.action == "retrieve":
            return CartSerializer
        elif self.action in ["create", "update"]:
            return POSTCartSerializer
        elif self.action == "destroy":
            return DestroyCartSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        """
        Возвращает контекст сериализатора с дополнительными данными.
        """
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        """
        Возвращает корзину текущего пользователя.
        """
        if getattr(self, "swagger_fake_view", False):
            return Cart.objects.none()
        return Cart.objects.filter(user=self.request.user)

    def get_user_cart(self):
        """
        Возвращает корзину пользователя или ответ с ошибкой,
        если корзина не найдена.
        """
        cart = self.get_queryset().first()
        if not cart:
            return Response(
                {"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return cart

    @swagger_auto_schema(
        operation_id="check_cart",
        operation_description="Просмотр корзины",
        responses={200: CartSerializer, 404: "Cart not found"},
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Возвращает текущую корзину пользователя.
        """
        cart = self.get_user_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_id="add_product",
        request_body=POSTCartSerializer,
        responses={201: CartSerializer, 400: "Invalid data", 404: "Product not found"},
        operation_description="Добавление товара в корзину",
    )
    def create(self, request, *args, **kwargs):
        """
        Добавляет товар в корзину текущего пользователя.
        """
        cart = get_or_create_user_cart(user=request.user)
        post_serializer = self.get_serializer(data=request.data)
        post_serializer.is_valid(raise_exception=True)

        product = post_serializer.validated_data["product"]
        quantity = post_serializer.validated_data["quantity"]

        add_product_to_cart(cart, product, quantity)

        get_serializer = CartSerializer(cart, context=self.get_serializer_context())
        return Response(
            {"detail": "Product added to cart.", "cart": get_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_id="update_product",
        responses={200: CartSerializer, 400: "Invalid data", 404: "Product not found"},
        operation_description="Изменение товара в корзине",
    )
    def update(self, request, *args, **kwargs):
        """
        Обновляет количество товара в корзине пользователя.
        """
        cart = self.get_user_cart()

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data.get("product")
        quantity = serializer.validated_data.get("quantity")

        try:
            update_cart_item_quantity(cart, product, quantity)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        get_serializer = CartSerializer(cart, context=self.get_serializer_context())
        return Response(get_serializer.data)

    @swagger_auto_schema(
        operation_id="destroy_product",
        operation_description="Удаление товара из корзины",
        manual_parameters=[
            openapi.Parameter(
                "product_id",
                openapi.IN_QUERY,
                description="ID продукта для удаления из корзины",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "Product removed from cart",
            400: "Product ID is required",
            404: "Product not found in cart",
        },
    )
    def destroy(self, request, *args, **kwargs):
        """
        Удаляет товар из корзины пользователя.
        Ожидает product_id как query параметр.
        """
        cart = self.get_user_cart()

        # Получаем product_id из query параметров запроса
        product_id = request.query_params.get("product_id")
        if not product_id:
            return Response(
                {"detail": "Product ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            remove_product_from_cart(cart, product_id)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        get_serializer = CartSerializer(cart, context=self.get_serializer_context())
        return Response(get_serializer.data, status=status.HTTP_200_OK)


class OrderAPIView(APIView):
    """
    API для создания заказа.
    Запускает фоновую задачу для обработки заказа и отправки уведомления.
    """

    @swagger_auto_schema(
        operation_id="create_order",
        responses={
            202: "Order is being processed",
            400: "Cart is empty",
            404: "Cart not found",
        },
    )
    def post(self, request):
        """
        POST /order — создание заказа.
        Запускает фоновую задачу для обработки заказа.
        """
        process_order.delay(request.user.id)

        return Response(
            {
                "detail": "Order is being processed. "
                "You will receive a notification when it is complete."
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AddressCoordinatesAPIView(APIView):
    """
    API для получения координат по адресу.
    Принимает адрес и возвращает координаты с помощью Яндекс.Карт.
    """

    @swagger_auto_schema(
        operation_id="get_coordinates",
        responses={200: "Coordinates returned", 400: "Invalid or missing address"},
    )
    def post(self, request):
        """
        POST /get-coordinates — получение координат по адресу.
        Ожидает адрес в данных запроса.
        """
        address = request.data.get("address")
        if not address:
            return Response(
                {"error": "Address is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        coordinates = get_coordinates(address)
        if "error" in coordinates:
            return Response(coordinates, status=status.HTTP_400_BAD_REQUEST)

        return Response(coordinates, status=status.HTTP_200_OK)
