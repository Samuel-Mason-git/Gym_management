from django.shortcuts import render
from .models import GymOwner, Gym, Member, Visit

def gym_owner_dashboard(request):
    context = {
        'gym_count': Gym.objects.count(),
        'gym_owners': GymOwner.objects.count(),

    }
    return render(request, 'dashboard.html', context)

