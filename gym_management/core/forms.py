from django import forms
from .models import Member


# Gym Code Login Form
class GymCodeForm(forms.Form):
    gym_code = forms.CharField(max_length=6, label="Gym Code", widget=forms.TextInput(attrs={
        'placeholder': 'Enter your gym code',
        'class': 'form-control'
    }))


