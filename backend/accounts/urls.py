from django.urls import path

from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_cliente, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
