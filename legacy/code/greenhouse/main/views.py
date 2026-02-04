import shutil
import os
import RPi.GPIO as GPIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from pathlib import Path
from main.models import Gpio

from .gpio import (
    get_gpio_funcs,
    set_gpio_state,
    get_gpio_states,
    set_gpio_value, 
    print_states,
    get_cpu_info, 
    get_gpio_banks,
    run_shell,
    )


BASE_DIR = Path(__file__).resolve().parent.parent


storage = FileSystemStorage(location='static/pics')



# Create your views here.

def homepage(request):
    return render(request=request, template_name='main/home.html')


def control_gpio_page(request):
    if request.method == 'GET':
        gpio_ports_from_device = [x for x in get_gpio_states() if x['bank_name']=='BANK0'][0]['gpio_ports']
        gpio_ports_from_db = list(map(lambda x: {'gpio_number': x.gpio_number, 'gpio_description': x.gpio_description, 'gpio_function': x.gpio_function}, Gpio.objects.all()))
        for port in gpio_ports_from_db:
            for gpio_port_from_device in gpio_ports_from_device:
                if gpio_port_from_device['gpio_number'] == port['gpio_number']:
                    if gpio_port_from_device['func'] == 'OUTPUT':
                        port['level'] = gpio_port_from_device['level']
                    break
        context = {
            'gpio_ports': gpio_ports_from_db,
        }
        return render(request=request, template_name='main/control.html', context=context)

def about_device_page(request):
    if request.method == 'GET':
        context = {
            'items_page': True,
            'rpi_info': GPIO.RPI_INFO,
            'gpio_version': str(GPIO.VERSION), 
        }
        return render(request=request, template_name='main/about_device.html', context=context)

def settingspage(request):
    if request.method == 'GET':
        context = {
            'items_page': True,
            'rpi_info': GPIO.RPI_INFO,
            'gpio_version': str(GPIO.VERSION), 
        }
        return render(request=request, template_name='main/settings.html', context=context)
    
def ports_settings_page(request):
    if request.method == 'GET':
        gpio_states_all = get_gpio_states()
        gpio_ports_from_device = [x for x in gpio_states_all if x['bank_name']=='BANK0'][0]['gpio_ports']
        ids_from_db: list = list(Gpio.objects.values_list('gpio_number', flat=True))
        for port in gpio_ports_from_device:
            if port['gpio_number'] in ids_from_db:
                port['assigned'] = True
            else: 
                port['assigned'] = False
        context = {
            'items_page': True,
            'gpio_ports': gpio_ports_from_device,
        }
        return render(request=request, template_name='main/ports_settings.html', context=context)
    
def ports_settings_assign(request):
    if request.method == 'POST':
        mode = request.POST['mode']
        gpio_number = int(request.POST['gpio-number'])
        gpio_description = request.POST['gpio-description']
        ids_from_db: list = list(Gpio.objects.values_list('gpio_number', flat=True))
        if gpio_number in ids_from_db:
            obj = get_object_or_404(Gpio, pk=gpio_number)
            Gpio.objects.filter(pk=gpio_number).delete()
            obj = Gpio(gpio_number=gpio_number, gpio_function=mode, gpio_description=gpio_description)
            # Сохраняем объект в базе данных
            obj.save()
        else:
            obj = Gpio(gpio_number=gpio_number, gpio_function=mode, gpio_description=gpio_description)
            # Сохраняем объект в базе данных
            obj.save()
        set_gpio_state(gpio_number=gpio_number, state=mode)
        return redirect('ports-settings')

def ports_control_set_output(request):
    gpio_number = request.POST['gpio_number']
    value = request.POST[f'gpio_port{gpio_number}']
    set_gpio_value(gpio_number=gpio_number, value=value)
    return redirect('control')


def ports_settings_disassign(request):
    if request.method == 'POST':
        gpio_number = int(request.POST['gpio_number'])
        run_shell(f"raspi-gpio set {gpio_number} op pn dl")
        run_shell(f"raspi-gpio set {gpio_number} ip pn")
        obj = get_object_or_404(Gpio, pk=gpio_number)
        obj.delete()
        return redirect('ports-settings')



def loginpage(request):
    if request.method == 'GET':
        return render(request=request, template_name='main/login.html')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request=request, user=user)
            return redirect('home')

        return redirect('login')


def logoutpage(request):
    logout(request=request)
    messages.success(
        request=request,
        message='You have been logged out')
    return redirect('home')


def registerpage(request):
    if request.method == 'GET':
        return render(request=request, template_name='main/register.html')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request=request, user=user)
            messages.success(
                request=request,
                message=f'You have registered your account successfully! Logged in as {username}')
            return redirect('home')

        messages.error(request=request,
                           message=form.errors)
        return redirect('register')
