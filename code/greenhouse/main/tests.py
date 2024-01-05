import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib import messages
from django.test import TestCase
from django.urls import reverse
from django.contrib.messages.storage.base import Message

from .gpio import (
    get_gpio_funcs,
    get_gpio_states,
    get_cpu_info,
    get_gpio_banks,
    print_states,
)


class UserRegisterTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_data = {
            'username': 'alex',
            'password1': 'MySuperStrongPassword123',
            'password2': 'MySuperStrongPassword123'
        }

        cls.user_broken_data = {
            'username': 'jake',
            'password1': 'MySuperStrongPassword123',
            'password2': 'MySuperStrongPassword1234'
        }

    def test_succ_register(self):
        response = self.client.get(
            # '/register/',
            reverse('register')
        )

        self.assertEqual(200, response.status_code)
        self.assertIn('inputUsername', response.content.decode())

        response = self.client.post(
            reverse('register'),
            data=self.user_data
        )

        self.assertEqual(302, response.status_code)

        new_user: User = get_user_model().objects.get(
            username=self.user_data['username']
        )

        self.assertIsNotNone(new_user)

        self.assertEqual(self.user_data['username'],
                         new_user.username)

    def test_fail_register(self):
        response = self.client.post(
            reverse('register'),
            data=self.user_broken_data
        )

        self.assertEqual(302, response.status_code)
        msgs: list[Message] = list(messages.get_messages(response.wsgi_request))
        error_msg = list(filter(lambda item: item.level_tag == "error", msgs))[0]
        self.assertIn("password2", error_msg.message)

class GpioTest(TestCase):
    def test_gpio_states(self):
        gpio_states_all = get_gpio_states()
        bank0 = [x for x in gpio_states_all if x['bank_name']=='BANK0'][0]
        print(json.dumps(bank0,indent=4))
        self.assertEqual('BANK0', bank0['bank_name'])
        self.assertEqual(0, bank0['bank_start'])
        self.assertEqual(27, bank0['bank_end'])

    def test_gpio_banks(self):
        banks = get_gpio_banks()
        print(json.dumps(banks, indent=4))
    
    def test_gpio_funcs(self):
        gpio_funcs_all = get_gpio_funcs()
        print(json.dumps(gpio_funcs_all, indent=4))
        #self.assertEqual('BANK0', bank0['bank_name'])
        #self.assertEqual(0, bank0['bank_start'])
        #self.assertEqual(27, bank0['bank_end'])
        

