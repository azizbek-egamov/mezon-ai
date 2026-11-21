from django.urls import path
from django.views.i18n import JavaScriptCatalog

from . import views

urlpatterns = [
    path("i18n/set/", views.set_language, name="set_language"),
    # Brauzer JS i uchun gettext katalogi (xuddi shu `django` domeni); ?l=<til> — kesh tilga bog'liq bo'lishi uchun
    path("jsi18n/", JavaScriptCatalog.as_view(domain="django"), name="jsi18n"),
]
