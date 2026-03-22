from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.category_list, name='category_list'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/manage/', views.product_manage, name='product_manage'),

    # Cart
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/item/<int:item_id>/', views.cart_update, name='cart_update'),
    path('cart/item/<int:item_id>/remove/', views.cart_remove, name='cart_remove'),

    # Addresses
    path('addresses/', views.address_list_create, name='address_list_create'),
    path('addresses/<int:pk>/', views.address_manage, name='address_manage'),

    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.create_order, name='create_order'),
    path('orders/verify-payment/', views.verify_payment, name='verify_payment'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),

    # Vendor
    path('vendor/products/', views.vendor_products, name='vendor_products'),

    # Admin
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/orders/<int:pk>/status/', views.admin_update_order_status, name='admin_update_order_status'),
]