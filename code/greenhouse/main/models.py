from django.db import models
from django.db.models import CharField, IntegerField


# Create your models here.

class Gpio(models.Model):
    gpio_number = IntegerField(primary_key=True, editable=True)
    gpio_description = CharField(max_length=100)
    gpio_function = CharField(max_length=10)

    def __str__(self):
        return f"{str(self.gpio_name)}, {str(self.gpio_bank)}"
