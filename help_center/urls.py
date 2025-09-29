# help_center/urls.py
from django.urls import path
from . import views

app_name = 'help_center'

urlpatterns = [
    path('', views.help_center, name='help_center'),
    path('category/<int:category_id>/', views.category_detail, name='category_detail'),
    path('article/<slug:slug>/', views.article_detail, name='article_detail'),
    path('search/', views.search_help, name='search_help'),
    path('faq/', views.faq_list, name='faq_list'),
]