
from django.urls import path

from . import views

urlpatterns = [
    path('', views.save_data, name='save_data'),
    path('v2/', views.save_data_v2),
    path('save_test/', views.save_test),
]
