from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    best_time = models.PositiveIntegerField(default=0) 

    def get_formatted_time(self):
        if self.best_time == 0:
            return "--:---"
        
        # Matematika pro milisekundy (celočíselná)
        total_seconds = self.best_time // 1000
        milis = self.best_time % 1000
        
        # Pokud chceš i minuty, kdyby byl někdo pomalý:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        if minutes > 0:
            return f"{minutes}:{seconds:02d}.{milis:03d}s"
        return f"{seconds}.{milis:03d}s"

    def __str__(self):
        return f"Profil: {self.user.username} (Rekord: {self.get_formatted_time()})"

# --- SIGNÁLY ---

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # Tohle zajistí, že se profil uloží při každé změně Usera 
        # a vytvoří se, pokud náhodou u starších uživatelů chybí
        if not hasattr(instance, 'profile'):
            Profile.objects.create(user=instance)
        instance.profile.save()