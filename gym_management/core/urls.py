from django.urls import path
from . import views 
from .views import gym_checkin_view, gym_dashboard, member_update_view

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('gym-owner-dashboard/', views.gym_owner_dashboard, name='gym_owner_dashboard'),
    path('member-dashboard/', views.member_dashboard, name='member_dashboard'),
    path('<slug:slug>/check-in/', gym_checkin_view, name='gym_checkin'),
    path('<slug:slug>/dashboard/', gym_dashboard, name='gym_dashboard'),
    path('member-update-info/', views.member_update_view, name='member_update_view'),
]