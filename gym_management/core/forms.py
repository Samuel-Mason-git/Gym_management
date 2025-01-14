from django import forms
from .models import Member, Gym
from django.contrib.auth.models import User
from .models import VerificationToken
from django.core.exceptions import ValidationError
from django.utils.timezone import now


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
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),  
            'email': forms.EmailInput(attrs={'class': 'form-control'}),  
        }
        labels = {
            'name': 'Gym Name',
            'address': 'Gym Location',
            'contact_number': 'Gym Contact Number',  
            'email': 'Gym Email Address',  
        }






# Form for checking verification tokens
class ManagerRegistrationForm(forms.Form):
    first_name = forms.CharField(label="First Name", max_length=150)
    last_name = forms.CharField(label="Last Name", max_length=150)
    email = forms.EmailField(label="Email", max_length=255)
    token = forms.CharField(label="Verification Code", max_length=8)
    username = forms.CharField(label="Username", max_length=150)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    def clean_token(self):
        token = self.cleaned_data.get("token")
        email = self.cleaned_data.get("email")
        
        # Validate token format
        if len(token) != 8 or not token.isdigit():
            raise ValidationError("The verification code must be 8 digits.")

        # Validate token in database
        try:
            verification_token = VerificationToken.objects.get(email=email, token=token)
            if verification_token.is_used:
                raise ValidationError("This verification code has already been used.")
            if verification_token.expires_at < now():
                raise ValidationError("This verification code has expired.")
        except VerificationToken.DoesNotExist:
            raise ValidationError("Invalid email or verification code.")
        
        return token
    
    def clean_first_name(self):
        return self.cleaned_data['first_name'].capitalize()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].capitalize()

    def clean_email(self):
        # Convert email to lowercase
        email = self.cleaned_data.get("email")
        return email.lower() if email else email    