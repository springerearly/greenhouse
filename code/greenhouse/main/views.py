import shutil
import os
import RPi.GPIO as GPIO

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from main.models import Item
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


storage = FileSystemStorage(location='static/pics')



# Create your views here.

def homepage(request):
    return render(request=request, template_name='main/home.html')


def statespage(request):
    if request.method == 'GET':
        context = {
            'items_page': True,
        }
        return render(request=request, template_name='main/states.html', context=context)

def about_device_page(request):
    if request.method == 'GET':
        context = {
            'items_page': True,
            'rpi_info': GPIO.RPI_INFO,
        }
        return render(request=request, template_name='main/about_device.html', context=context)

def loginpage(request):
    if request.method == 'GET':
        return render(request=request, template_name='main/login.html')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request=request, user=user)
            return redirect('items')

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
