from django.core.mail import send_mail
from django.conf import settings
import requests
from yookassa import Payment


def send_order_confirmation_email(user, order):
    """
    Отправляет письмо с подтверждением заказа.
    """
    subject = f'Ваш заказ #{order.id} был успешно создан'
    message = f'Здравствуйте, {user.username}!\n\nВаш заказ #{order.id} был успешно создан. Общая стоимость: {order.total_price}.'
    recipient_list = [user.email]

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )


def send_payment_url_email(user, payment_url):
    """
    Отправляет письмо с ссылкой на оплату.
    """
    subject = 'Ссылка на оплату'
    message = f'Оплатите ваш заказ, перейдя по ссылке: {payment_url}'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])


def create_payment(order):
    """
    Создает оплату заказа.
    """
    payment = Payment.create({
        'amount': {
            'value': str(order.total_price),
            'currency': 'RUB'
        },
        'confirmation': {
            'type': 'redirect',
            'return_url': 'https://ваш-домен.com/payment/success/'
        },
        'capture': True,
        'description': f'Оплата заказа #{order.id}'
    })
    return payment


def get_coordinates(address):
    """
    Получает координаты по адресу через Яндекс.Карты API.
    """
    url = 'https://geocode-maps.yandex.ru/1.x/'
    params = {
        'apikey': settings.YANDEX_API_KEY,
        'geocode': address,
        'format': 'json'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        try:
            response_data = response.json()
            geo_object = response_data['response']['GeoObjectCollection']['featureMember']
            point = geo_object[0]['GeoObject']['Point']
            pos = point['pos']
            lon, lat = pos.split()
            return {'longitude': lon, 'latitude': lat}
        except (IndexError, KeyError):
            return {'error': 'Address not found'}
    else:
        return {'error': 'Failed to connect to Yandex API'}
