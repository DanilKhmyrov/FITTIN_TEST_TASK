import pytest
from django.urls import reverse

from api.models import CartItem

pytestmark = pytest.mark.django_db


def test_get_product_list(api_client, product):
    url = reverse("product-list")
    response = api_client.get(url)
    assert response.status_code == 200
    assert len(response.data) > 0


def test_get_product_detail(api_client, product):
    url = reverse("product-detail", args=[product.id])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data["name"] == product.name


def test_get_category_list(api_client, category):
    url = reverse("category-list")
    response = api_client.get(url)
    assert response.status_code == 200
    assert len(response.data) > 0


def test_add_product_to_cart(auth_client, product, cart):
    url = reverse("cart")
    data = {"product": product.id, "quantity": 2}
    response = auth_client.post(url, data)
    assert response.status_code == 201
    assert response.data["cart"]["products"][0]["id"] == product.id
    assert response.data["cart"]["products"][0]["quantity"] == 2


def test_update_cart_item_quantity(auth_client, product, cart):
    CartItem.objects.create(cart=cart, product=product, quantity=1)
    url = reverse("cart")
    data = {"product": product.id, "quantity": 5}

    response = auth_client.patch(url, data)

    assert response.status_code == 200
    assert response.data["products"][0]["quantity"] == 5


def test_remove_product_from_cart(auth_client, product, cart):
    CartItem.objects.create(cart=cart, product=product, quantity=2)
    url = reverse("cart") + f"?product_id={product.id}"

    response = auth_client.delete(url)

    assert response.status_code == 200
    assert len(response.data["products"]) == 0


def test_view_cart(auth_client, cart, product):
    CartItem.objects.create(cart=cart, product=product, quantity=3)
    url = reverse("cart")
    response = auth_client.get(url)
    assert response.status_code == 200
    assert response.data["products"][0]["quantity"] == 3


def test_create_order(auth_client, cart, product):
    CartItem.objects.create(cart=cart, product=product, quantity=2)
    url = reverse("order")
    response = auth_client.post(url)
    assert response.status_code == 202
    assert (
        response.data["detail"]
        == "Order is being processed. You will receive a notification when it is complete."
    )
