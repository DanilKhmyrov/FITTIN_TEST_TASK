from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Category(models.Model):
    """
    Модель для категорий товаров.
    Поддерживает иерархическую структуру категорий
    через связь 'parent', позволяющую задавать подкатегории.
    """

    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subcategories",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]


class Product(models.Model):
    """
    Модель для товаров. Поддерживает связь с категориями и хранит описание,
    цену, изображение и дополнительные характеристики в формате JSON.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="product_images/", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    characteristics = models.JSONField(blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-price"]


class AbstractContainer(models.Model):
    """
    Абстрактная модель для контейнеров, таких как корзина и заказ.
    Хранит ссылку на пользователя, дату создания и общую стоимость.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="%(class)s")
    created_at = models.DateTimeField(default=timezone.now)
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        verbose_name = "Container"
        verbose_name_plural = "Containers"

    def __str__(self):
        return f"{self.__class__.__name__} of {self.user.username}"

    def calculate_total_price(self):
        """
        Пересчитывает общую стоимость всех элементов в контейнере.
        Вызывается при изменении содержимого корзины или заказа.
        """
        self.total_price = sum(
            item.product.price * item.quantity for item in self.items.all()
        )
        self.save()


class AbstractContainerItem(models.Model):
    """
    Абстрактная модель для элементов, содержащихся в корзине или заказе.
    Хранит ссылку на продукт и его количество.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True
        ordering = ["product"]
        verbose_name = "Container Item"
        verbose_name_plural = "Container Items"

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.__class__.__name__}"

    def get_total_price(self):
        """
        Возвращает общую стоимость (цена * количество).
        """
        return self.product.price * self.quantity


class Cart(AbstractContainer):
    """
    Модель для корзины пользователя. Расширяет AbstractContainer.
    """

    class Meta(AbstractContainer.Meta):
        verbose_name = "Cart"
        verbose_name_plural = "Carts"


class CartItem(AbstractContainerItem):
    """
    Модель для элементов корзины. Содержит продукт и его количество в корзине.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")

    class Meta(AbstractContainerItem.Meta):
        unique_together = ("cart", "product")
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"


class Order(AbstractContainer):
    """
    Модель для заказа. Содержит ссылки на продукты через модель OrderItem.
    """

    products = models.ManyToManyField(Product, through="OrderItem")

    class Meta(AbstractContainer.Meta):
        verbose_name = "Order"
        verbose_name_plural = "Orders"


class OrderItem(AbstractContainerItem):
    """
    Модель для элементов заказа.
    Хранит информацию о продукте и его количестве в заказе.
    """

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="order_items"
    )

    class Meta(AbstractContainerItem.Meta):
        unique_together = ("order", "product")
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
