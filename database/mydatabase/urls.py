from django.urls import path
from django.contrib import admin 
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('patchn/', views.patchn, name='patchn'),
    path('qan/', views.qan, name='qan'),
    path('profile/', views.profile, name='profile'),
    path('comments/', views.comments, name='comments'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout')
]