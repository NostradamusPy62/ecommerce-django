# help_center/admin.py
from django.contrib import admin
from .models import HelpCategory, HelpArticle, FAQ

@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'description']
    prepopulated_fields = {}

@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_featured', 'view_count']
    list_filter = ['category', 'is_featured']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order']
    list_filter = ['category']
    search_fields = ['question', 'answer']