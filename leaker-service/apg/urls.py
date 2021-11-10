from django.urls import path

from . import views

urlpatterns = [
    path('<str:inc_method>/', views.get_attack_page, name='get_attack_page'),
    path('test/<str:inc_method>/', views.get_test_page, name='get_test_page'),
]
