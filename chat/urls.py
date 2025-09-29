from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.ChatView.as_view(), name='chat'),  # ← CAMBIA 'chat_view' por 'chat'
    path('api/send-message/', views.ChatView.as_view(), name='send_message'),
    path('api/products-by-category/', views.ProductsByCategoryView.as_view(), name='products_by_category'),
    path('stock/pdf/', views.GenerateStockPDFView.as_view(), name='generate_stock_pdf'),
    path('api/compare-products/', views.CompareProductsView.as_view(), name='compare_products'),
    path('api/stock-list/', views.get_stock_list, name='get_stock_list'),
]