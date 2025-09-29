from django import forms

class ChatForm(forms.Form):
    message = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Escribe tu mensaje aquí...',
            'autocomplete': 'off'
        }),
        max_length=500
    )