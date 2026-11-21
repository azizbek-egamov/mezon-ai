from django.urls import path

from . import views

urlpatterns = [
    path("billing/", views.billing_page, name="billing"),
    path("api/billing/usage", views.api_usage, name="billing_usage"),
]
