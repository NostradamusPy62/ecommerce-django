from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Gestión de productos
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/edit/<int:product_id>/', views.product_edit, name='product_edit'),
    path('products/delete/<int:product_id>/', views.product_delete, name='product_delete'),
    
    # Gestión de categorías
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/edit/<int:category_id>/', views.category_edit, name='category_edit'),
    path('categories/delete/<int:category_id>/', views.category_delete, name='category_delete'),
    
    # Gestión de pedidos
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/update-status/<int:order_id>/', views.order_update_status, name='order_update_status'),
    
    # Gestión de usuarios (solo superadmin)
    path('users/', views.user_list, name='user_list'),
    path('users/edit-role/<int:user_id>/', views.user_edit_role, name='user_edit_role'),
    
    # Reportes
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/products/', views.products_report, name='products_report'),
    path('reports/users/', views.users_report, name='users_report'),
    
    # Chat (historial)
    path('chat/history/', views.chat_history, name='chat_history'),
]