from celery import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from yookassa import Configuration

from .models import Cart, Order, OrderItem
from .utils import (create_payment, send_order_confirmation_email,
                    send_payment_url_email)

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
            return {"error": "Cart is empty."}

        order = Order.objects.create(
            user_id=user_id, total_price=cart.total_price)

        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
            )

        try:
            payment = create_payment(order)
            confirmation_url = payment.get(
                "confirmation", {}).get("confirmation_url")
            if not confirmation_url:
                raise ValueError("No confirmation URL in payment response.")
        except Exception as e:
            return {"error": f"Failed to create payment: {e}"}

        cart.items.all().delete()
        cart.total_price = 0
        cart.save()

        send_order_confirmation_email(order.user, order)
        send_payment_url_email(order.user, confirmation_url)

        return {"order_id": order.id, "payment_url": confirmation_url}

    except Cart.DoesNotExist:
        return {"error": "Cart not found."}
    except ObjectDoesNotExist as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
