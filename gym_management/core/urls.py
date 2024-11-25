from django.urls import path
from . import views  # Import views from the same directory

urlpatterns = [
    path('dashboard/', views.gym_owner_dashboard, name='gym_owner_dashboard'),
]