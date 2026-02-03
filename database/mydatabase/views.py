
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import RegisterForm




def home(request):
    return render(request, "main/hl_stranka.html")

def about(request):
    return render(request, "main/about.html")

def patchn(request):
    return render(request, "main/patchn.html")

def qan(request):
    return render(request, "main/qan.html")

def profile(request):
    return render(request, "main/profile.html")

def comments(request):
    return render(request, "main/comments.html")



from django.contrib import messages


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"]
            )

            login(request, user)  # automatické přihlášení
            messages.success(request, "Registration successful!")

            return redirect("home")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})

from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")  # checkbox

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Pokud nechce "remember me", session vyprší po zavření prohlížeče
            if not remember_me:
                request.session.set_expiry(0)  # vyprší po zavření prohlížeče

            return redirect("home")
        else:
            return render(request, "login_failed.html")  # volitelně

    return redirect("home")

def logout_view(request):
    logout(request)
    return redirect("home")  # po odhlášení přesměruj na domovskou stránku
