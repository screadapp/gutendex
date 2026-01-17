from django.urls import include, re_path
from django.views.generic import TemplateView

from rest_framework import routers

from books import views


router = routers.DefaultRouter()
router.register(r'books', views.BookViewSet)

from django.http import HttpResponse

urlpatterns = [
    re_path(r'^health/?$', lambda request: HttpResponse("OK")),
    re_path(r'^$', TemplateView.as_view(template_name='home.html')),
    re_path(r'^', include(router.urls)),
]
