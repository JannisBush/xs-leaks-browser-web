from django.urls import path

from . import views

urlpatterns = [
    path('<int:id_number>/<str:auth_status>/', views.leaks, name='leaks'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('test/', views.test_login, name='test'),
    path('ver/', views.get_ver, name='ver'),
    path('save_dict/', views.save_dict, name='save_dict'),
    path('info_url/<int:url_id>/', views.get_info, name='info_url'),
    path('set_cookies/', views.set_cookies, name='set_cookies'),
    path('check_cookies/', views.check_cookies, name='check_cookies'),
]
