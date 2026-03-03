from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    play_time = models.PositiveIntegerField(default=0) # Čas v sekundách

    def get_formatted_time(self):
        minutes = self.play_time // 60
        seconds = self.play_time % 60
        return f"{minutes}m {seconds}s"

    def __str__(self):
        return f"Profil uživatele {self.user.username}"

# AUTOMATICKÉ VYTVOŘENÍ PROFILU
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Kontrola, zda profil existuje, než ho zkusíme uložit
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # Pokud neexistuje (u starých uživatelů), vytvoříme ho
        Profile.objects.create(user=instance)