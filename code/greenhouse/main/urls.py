from django.urls import path
from main import views

urlpatterns = [
    path('', views.homepage, name='index'),
    path('home/', views.homepage, name='home'),
    path('items/', views.itemspage, name='items'),
    path('my-items/', views.my_itemspage, name='my-items'),
    path('add-item/', views.add_itempage, name='add-item'),
    path('delete-item/', views.delete_itempage, name='delete-item'),
    path('login/', views.loginpage, name='login'),
    path('logout/', views.logoutpage, name='logout'),
    path('register/', views.registerpage, name='register'),
]
