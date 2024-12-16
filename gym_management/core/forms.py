from django import forms
from .models import Member, Gym
from django.contrib.auth.models import User

# Gym Code Login Form
class GymCodeForm(forms.Form):
    gym_code = forms.CharField(max_length=6, label="Gym Code", widget=forms.TextInput(attrs={
        'placeholder': 'Enter your gym code',
        'class': 'form-control'
    }))




# Member personal details update
class MemberUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,  # Make the field optional
        label='First Name',
        help_text="Enter your first name or leave unchanged."
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,  # Make the field optional
        label='Last Name',
        help_text="Enter your last name or leave unchanged."
    )
    email = forms.EmailField(
        required=False,  # Make the field optional
        label="Email",
        help_text="Ensure this is your valid email address."
    )

    class Meta:
        model = Member
        fields = ['contact_number', 'date_of_birth', 'address']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'contact_number': "Enter your phone number.",
            'date_of_birth': "Use the format YYYY-MM-DD.",
            'address': "Enter your current address.",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Pre-populate fields from the User model
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def save(self, commit=True):
        member = super().save(commit=False)

        # Update related user fields only if the user provides a value
        user = member.user
        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.last_name = self.cleaned_data.get('last_name', user.last_name)
        user.email = self.cleaned_data.get('email', user.email)

        if commit:
            user.save()
            member.save()
        return member
    



# Form for updating gym information
class GymUpdateForm(forms.ModelForm):
    class Meta:
        model = Gym
        fields = ['name', 'address', 'contact_number', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),  # Added class for contact number
            'email': forms.EmailInput(attrs={'class': 'form-control'}),  # Added class for email
        }
        labels = {
            'name': 'Gym Name',
            'address': 'Gym Location',
            'contact_number': 'Contact Number',  # Custom label
            'email': 'Email Address',  # Custom label
        }
