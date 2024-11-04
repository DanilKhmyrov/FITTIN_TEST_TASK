from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (AddressCoordinatesAPIView, CartViewSet, CategoryViewSet,
                    OrderAPIView, ProductsAPIView, ProductViewSet)

router_v1 = DefaultRouter()

router_v1.register(r"product", ProductViewSet)
router_v1.register(r"categories", CategoryViewSet)


urlpatterns = [
    path("v1/", include("djoser.urls")),
    path("v1/", include("djoser.urls.jwt")),
    path("v1/", include(router_v1.urls)),
    path(
        "v1/get-coordinates/",
        AddressCoordinatesAPIView.as_view(),
        name="get_coordinates",
    ),
    path("v1/products/", ProductsAPIView.as_view()),
    path("v1/order/", OrderAPIView.as_view(), name="order"),
    path(
        "v1/cart/",
        CartViewSet.as_view(
            {
                "get": "retrieve",
                "post": "create",
                "patch": "update",
                "delete": "destroy",
            }
        ),
        name="cart",
    ),
]
