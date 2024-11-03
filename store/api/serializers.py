from rest_framework import serializers

from .models import Cart, CartItem, Category, Order, Product


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели продукта.
    Используется для представления полной информации о продукте.
    """

    class Meta:
        model = Product
        fields = '__all__'


class CategoryFilterSerializer(serializers.Serializer):
    """
    Сериализатор фильтрации товаров по категории.
    """

    category = serializers.IntegerField(
        required=False, help_text='ID категории для фильтрации товаров')


class RecursiveIDSerializer(serializers.Serializer):
    """
    Рекурсивный сериализатор для вложенных категорий, позволяющий
    сериализовать подкатегории на основе их ID.
    """

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'subcategories': RecursiveIDSerializer(
                instance.subcategories.all(), many=True).data
        }


class CategoriesSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели категорий товаров, с поддержкой
    вложенных подкатегорий и родительской категории.
    """

    subcategories = RecursiveIDSerializer(
        many=True, read_only=True, allow_null=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True
    )

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'subcategories']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('parent') is None:
            representation.pop('parent')
        return representation


class CartItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения информации о товарах в корзине.
    """

    id = serializers.IntegerField(source='product.id')
    name = serializers.CharField(source='product.name')
    price = serializers.DecimalField(
        source='product.price', max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField(
        min_value=1, help_text='Количество товара должно быть положительным')

    class Meta:
        model = CartItem
        fields = ['id', 'name', 'price', 'quantity']


class CartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для корзины, с отображением товаров и общей суммы.
    """

    products = CartItemSerializer(source='items', many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ('products', 'total_price')

    def to_representation(self, instance):
        """
        Добавляет корзину в контекст при сериализации.
        """

        self.context['cart'] = instance
        return super().to_representation(instance)


class POSTCartSerializer(serializers.Serializer):
    """
    Сериализатор для добавления товара в корзину.
    Ожидает ID товара и его количество.
    """

    product = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True, min_value=1)

    def validate_product(self, value):
        try:
            product = Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Продукт с таким ID не найден.')
        return product


class DestroyCartSerializer(serializers.Serializer):
    """
    Сериализатор для удаления товара из корзины.
    Ожидает ID продукта.
    """

    product = serializers.IntegerField(
        required=True, help_text='ID товара для удаления из корзины')


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели заказа.
    Отображает все данные, связанные с заказом.
    """

    def validate_total_price(self, value):
        """
        Проверяет, что общая стоимость заказа не отрицательная.
        """
        if value < 0:
            raise serializers.ValidationError(
                'Общая стоимость заказа не может быть отрицательной.')
        return value

    class Meta:
        model = Order
        fields = '__all__'
