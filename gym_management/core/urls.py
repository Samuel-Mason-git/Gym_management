from django.urls import path
from . import views  # Import views from the same directory

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('gym-owner-dashboard/', views.gym_owner_dashboard, name='gym_owner_dashboard'),
    path('member-dashboard/', views.member_dashboard, name='member_dashboard'),
]