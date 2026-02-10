from django import forms
from django.contrib.auth.models import User


class RegisterForm(forms.Form):
    username = forms.CharField(
        min_length=5,
        max_length=150,
        required=True
    )
    email = forms.EmailField(
        required=True
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput,
        required=True
    )
    password_confirm = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput,
        required=True
    )

    def clean_username(self):
        username = self.cleaned_data['username']

        if ' ' in username:
            raise forms.ValidationError("Username cannot contain spaces.")

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")

        return username

    def clean_email(self):
        email = self.cleaned_data['email']

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Passwords do not match.")
