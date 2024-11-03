from rest_framework.exceptions import ValidationError

from .models import Cart, CartItem


def get_or_create_user_cart(user):
    """
    Возвращает корзину пользователя или создаёт её, если она не существует.
    """
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def calculate_cart_total_price(cart):
    """
    Пересчитывает общую стоимость корзины.
    """
    total_price = sum(item.product.price *
                      item.quantity for item in cart.items.all())
    cart.total_price = total_price
    cart.save()
    return total_price


def add_product_to_cart(cart, product, quantity):
    """
    Добавляет товар в корзину или обновляет количество, если товар уже в корзине.
    """
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product)
    cart_item.quantity = cart_item.quantity + quantity if not created else quantity
    cart_item.save()

    calculate_cart_total_price(cart)


def update_cart_item_quantity(cart, product, quantity):
    """
    Обновляет количество товара в корзине.
    """
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        cart_item.quantity = quantity
        cart_item.save()
    except CartItem.DoesNotExist:
        raise ValueError('Product not found in cart')

    calculate_cart_total_price(cart)


def remove_product_from_cart(cart, product_id):
    """
    Удаляет товар из корзины и пересчитывает общую стоимость корзины.
    """
    try:
        cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
        cart_item.delete()
    except CartItem.DoesNotExist:
        raise ValidationError({'detail': 'Product not found in cart'})

    calculate_cart_total_price(cart)
