from django.urls import path
from django.contrib import admin 
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('patchn/', views.patchn, name='patchn'),
    path('profile/', views.profile, name='profile'),
    path('comments/', views.comments, name='comments'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/update_playtime/', views.update_playtime, name='update_playtime'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('api/update_playtime/', views.update_playtime, name='update_playtime'),
]