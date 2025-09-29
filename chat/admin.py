from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key', 'timestamp', 'truncated_user_message']
    list_filter = ['timestamp', 'user']
    search_fields = ['user_message', 'bot_response', 'user__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def truncated_user_message(self, obj):
        return obj.user_message[:50] + '...' if len(obj.user_message) > 50 else obj.user_message
    truncated_user_message.short_description = 'Mensaje del usuario'