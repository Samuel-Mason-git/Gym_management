from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import GymOwner, Member

# Login View with conditional dashboard redirecting dependant on what status a user account is
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Authenticate the user
            user = form.get_user()
            login(request, user)
            
            # Check if the user is a Gym Owner or Member and redirect accordingly
            try:
                gym_owner = GymOwner.objects.get(user=user)
                # Redirect to gym owner's dashboard if user is a gym owner
                return redirect('gym_owner_dashboard')
            except GymOwner.DoesNotExist:
                pass
            
            try:
                member = Member.objects.get(user=user)
                # Redirect to member's dashboard if user is a member
                return redirect('member_dashboard')
            except Member.DoesNotExist:
                pass

            messages.error(request, "User role not found.")
            return redirect('login')

        else:
            messages.error(request, "Invalid username or password.")
    
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


# Login and render request for Gym Ownrs
@login_required
def gym_owner_dashboard(request):
    user = request.user
    try:
        gym_owner = GymOwner.objects.get(user=user)
        gyms = gym_owner.gyms.all()
        gym_count = gym_owner.gyms.count()
        gym_owner_name = gym_owner.user.get_full_name()
        gym_data = []
        for gym in gyms:
            member_count = gym.members.count()
            gym_data.append({
                'gym_name': gym.name,
                'member_count': member_count,
            })
        
        
        context = {
            'role': 'Gym Owner',
            'gym_count': gym_count,
            'gym_owner_name': gym_owner_name,
            'gym_data': gym_data,
        }
        return render(request, 'gym_owner_dashboard.html', context)
    except GymOwner.DoesNotExist:
        messages.error(request, "No gym owner profile found.")
        return redirect('login')



# Login and render request for Members
@login_required
def member_dashboard(request):
    user = request.user
    try:
        member = Member.objects.get(user=user)
        context = {
            'role': 'Member',
            'gym_name': member.gym.name,
            'join_date': member.join_date,
        }
        return render(request, 'member_dashboard.html', context)
    except Member.DoesNotExist:
        messages.error(request, "No member profile found.")
        return redirect('login')




# Signup function request
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account has been created successfully.')
            return redirect('login')  # Redirect to login page after successful signup
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form})
