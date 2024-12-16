from django.urls import path
from . import views 
from .views import *

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('gym-owner-dashboard/', views.gym_owner_dashboard, name='gym_owner_dashboard'),
    path('member-dashboard/', views.member_dashboard, name='member_dashboard'),
    path('<slug:slug>/check-in/', views.gym_checkin_view, name='gym_checkin'),
    path('<slug:slug>/dashboard/', views.gym_dashboard, name='gym_dashboard'),
    path('member-update-info/', views.member_update_view, name='member_update_view'),
    path('gym-owner-update-info/', views.gym_owner_update_view, name='gym_owner_update_view'),
    path('<slug:slug>/settings/', views.gym_settings, name='gym_settings'),
]