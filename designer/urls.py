from django.urls import path
from . import views

app_name = 'designer'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
