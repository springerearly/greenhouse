from django.db import models
from django.db.models import CharField, IntegerField, ForeignKey, BooleanField
from django.contrib.auth.models import User


# Create your models here.

class Item(models.Model):
    owner = ForeignKey(User, default=None, blank=True, on_delete=models.SET_NULL, null=True)
    name = CharField(max_length=255)
    price = IntegerField()
    description = CharField(max_length=1024)
    image_url = CharField(max_length=512)
    is_for_sale = BooleanField(default=True)

    def __str__(self):
        return f"{str(self.name)}, {str(self.image_url)}"
