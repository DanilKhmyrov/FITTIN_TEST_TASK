from celery import shared_task
from django.conf import settings
from yookassa import Configuration

from .utils import (send_order_confirmation_email,
                    send_payment_url_email, create_payment)
from .models import Cart, Order, OrderItem


Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


@shared_task
def process_order(user_id):
    """
    Задача Celery для создания заказа, создания платежа и отправки уведомления.
    """
    try:
        cart = Cart.objects.get(user_id=user_id)
        if not cart.items.exists():
            return {'error': 'Cart is empty.'}

        order = Order.objects.create(
            user_id=user_id, total_price=cart.total_price)

        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
            )

        payment = create_payment(order)

        cart.items.all().delete()
        cart.total_price = 0
        cart.save()
        try:
            confirmation_url = payment.confirmation.confirmation_url
        except Exception as e:
            return {'error': f'Failed to create payment: {e}'}
        send_order_confirmation_email(order.user, order)
        send_payment_url_email(order.user, confirmation_url)

        return {'order_id': order.id, 'payment_url': confirmation_url}

    except Cart.DoesNotExist:
        return {'error': 'Cart not found.'}
    except Exception as e:
        return {'error': str(e)}
