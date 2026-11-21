from django.urls import path

from . import views

urlpatterns = [
    path("templates/", views.template_list, name="template_list"),
    path("templates/<uuid:template_id>/", views.template_fill, name="template_fill"),
]
