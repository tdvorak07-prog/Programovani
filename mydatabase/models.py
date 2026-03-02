from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    play_time = models.PositiveIntegerField(default=0)

    def get_formatted_time(self):
        minutes = self.play_time // 60
        seconds = self.play_time % 60
        return f"{minutes}m {seconds}s"

    def __str__(self):
        return f"Profil uživatele {self.user.username}"

