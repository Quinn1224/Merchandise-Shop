from django.urls import path
from . import views

app_name = 'merchandiseshop'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/remove/<str:item_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),
]