from django import forms
from .models import ReviwRating

class ReviewForm(forms.ModelForm):

    class Meta:
        model = ReviwRating
        fields = ['subject', 'review', 'rating']