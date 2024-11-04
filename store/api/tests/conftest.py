import pytest
from rest_framework.test import APIClient

from api.models import Cart, CartItem, Category, Order, Product


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="testuser", password="testpass"
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def category():
    return Category.objects.create(name="Test Category")


@pytest.fixture
def product(category):
    return Product.objects.create(name="Test Product", price=100.0, category=category)


@pytest.fixture
def cart(user):
    return Cart.objects.create(user=user)
