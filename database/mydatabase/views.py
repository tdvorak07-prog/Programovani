
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
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




def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"]
            )
            return redirect("home")
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")

    return redirect("home")