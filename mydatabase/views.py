
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import RegisterForm
from django.contrib import messages
# --- PŘIDANÉ IMPORTY PRO PYGAME ---
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
# ---------------------------------



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
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Kontrola, zda jsou všechna pole vyplněná
        if not username or not email or not password:
            messages.error(request, "Všechna pole musí být vyplněna.")
            return redirect("home")

        # Kontrola, zda uživatel již neexistuje
        if User.objects.filter(username=username).exists():
            messages.error(request, "Tento uživatel již existuje.")
            return redirect("home")

        try:
            # Vytvoření uživatele - create_user automaticky zahashuje heslo a uloží do DB
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            login(request, user)
            messages.success(request, "Registrace proběhla úspěšně!")
            return redirect("home")
            
        except Exception as e:
            messages.error(request, f"Něco se pokazilo: {e}")
            return redirect("home")

    return redirect("home")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if not remember_me:
                request.session.set_expiry(0)
            return redirect("home")

        # MÍSTO render(request, "login_failed.html")
        messages.error(request, "Špatné jméno nebo heslo!")
        return redirect("home")

    return redirect("home")
    

def logout_view(request):
    logout(request)
    return redirect("home")  # po odhlášení přesměruj na domovskou stránku
@csrf_exempt  # Nutné, aby se Pygame mohlo připojit bez CSRF tokenu
def api_login(request):
    if request.method == "POST":
        try:
            # Načtení dat, která poslal Pygame (username a password)
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")

            # Klasické Django ověření
            user = authenticate(username=username, password=password)

            if user is not None:
                # Přihlášení proběhlo úspěšně
                return JsonResponse({
                    "status": "success", 
                    "username": user.username,
                    "message": "Vítej v Speed Hell!"
                }, status=200)
            else:
                # Špatné údaje
                return JsonResponse({
                    "status": "error", 
                    "message": "Neplatné jméno nebo heslo."
                }, status=401)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error", "message": "Povolen je pouze POST."}, status=405)

@csrf_exempt
def update_playtime(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        # Čas poslaný z Pygame v milisekundách
        new_time_ms = data.get('play_time', 0) 
        
        try:
            user = User.objects.get(username=username)
            # Přičteme čas k existujícímu (převod na sekundy pro databázi)
            user.profile.play_time += int(new_time_ms / 1000)
            user.profile.save()
            return JsonResponse({'status': 'success'})
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
