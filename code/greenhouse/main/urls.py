from django.urls import path
from django.contrib.auth.decorators import login_required
from main import views

urlpatterns = [
    path('', views.homepage, name='index'),
    path('home/', views.homepage, name='home'),
    path('states/', login_required(views.statespage), name='states'),
    path('settings/', login_required(views.settingspage), name='settings'),
    path('about-device/', views.about_device_page, name='about_device'),
    path('login/', views.loginpage, name='login'),
    path('logout/', views.logoutpage, name='logout'),
    path('register/', views.registerpage, name='register'),
]
