from django.urls import path
from django.contrib.auth.decorators import login_required
from main import views

urlpatterns = [
    path('', views.homepage, name='index'),
    path('home/', views.homepage, name='home'),
    path('control/', login_required(views.control_gpio_page), name='control'),
    path('ports-settings/', login_required(views.ports_settings_page), name='ports-settings'),
    path('assign/', login_required(views.ports_settings_assign), name='ports-settings-assign'),
    path('set-output/', login_required(views.ports_control_set_output), name='ports-control-set-output'),
    path('about-device/', views.about_device_page, name='about_device'),
    path('login/', views.loginpage, name='login'),
    path('logout/', views.logoutpage, name='logout'),
    path('register/', views.registerpage, name='register'),
]
