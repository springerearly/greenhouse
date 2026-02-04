from django.core.management.base import BaseCommand, CommandError
from main.models import Gpio
from main.gpio import (
    set_gpio_state
)


class Command(BaseCommand):
    help = 'My custom startup command'

    def handle(self, *args, **kwargs):
        try:
            for gpio in Gpio.objects.all():
                set_gpio_state(gpio_number=gpio.gpio_number, state=gpio.gpio_function)
        except:
            raise CommandError('Initalization failed.')