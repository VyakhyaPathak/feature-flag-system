"""
Day 18 - Django integration example: urls.py

Reference code - wires the views in views.py to URLs, so you can see the
whole request path: URL -> view -> flagkit -> Feature Flag API.
"""
from django.urls import path
from . import views

urlpatterns = [
    path("checkout/", views.checkout_view, name="checkout"),
    path("beta-banner/", views.beta_banner_view, name="beta_banner"),
    path("checkout-for-user/", views.checkout_for_user_view, name="checkout_for_user"),
]
