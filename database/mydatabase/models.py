from django.db import models

class lol(models.Model):
    title = models.CharField(max_length=200)
    finished = models.BooleanField(default=False)