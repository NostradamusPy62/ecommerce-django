from django.db import models
from django.conf import settings
from django.utils import timezone

class ChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Usuario"
    )
    user_message = models.TextField(
        verbose_name="Mensaje del usuario",
        default="",  # ← AGREGA ESTO
        blank=True
    )
    bot_response = models.TextField(
        verbose_name="Respuesta del bot", 
        default="",  # ← AGREGA ESTO
        blank=True
    )
    session_key = models.CharField(
        max_length=100, 
        blank=True, 
        default="",  # ← AGREGA ESTO
        verbose_name="Clave de sesión (para usuarios anónimos)"
    )
    timestamp = models.DateTimeField(
        default=timezone.now, 
        verbose_name="Fecha y hora"
    )
    
    class Meta:
        verbose_name = "Mensaje de chat"
        verbose_name_plural = "Mensajes de chat"
        ordering = ['-timestamp']
    
    def __str__(self):
        user_info = self.user.username if self.user else f"Anónimo ({self.session_key})"
        return f"{user_info} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"