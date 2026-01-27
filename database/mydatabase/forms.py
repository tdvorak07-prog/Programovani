from django import forms
from django.contrib.auth.models import User


class RegisterForm(forms.Form):
    username = forms.CharField(min_length=5, max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    password = forms.CharField(min_length=8, max_length=100)

    def clean_username(self):
        username = self.cleaned_data['username']
      

        if ' ' in username :
                raise forms.ValidationError("Username cannot contain spaces.")
        
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")

        return username