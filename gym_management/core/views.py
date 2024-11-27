from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import GymOwner, Member, Visit, Gym
from .forms import GymCodeForm
from django.utils.timezone import now

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
            'member_code': member.gym_code if member.gym_code else "No code assigned",
            'member_name': user.get_full_name().capitalize() or user.username.capitalize(),
        }
        return render(request, 'member_dashboard.html', context)
    except Member.DoesNotExist:
        messages.error(request, "No member profile found.")
        return redirect('login')


# Gym checkin View (the render for the check-in page for each gym)
def gym_checkin_view(request, slug):
    # Fetch gym by its slug
    gym = get_object_or_404(Gym, slug=slug)

    if request.method == 'POST':
        form = GymCodeForm(request.POST)
        if form.is_valid():
            gym_code = form.cleaned_data['gym_code']
            try:
                member = Member.objects.get(gym_code=gym_code, gym=gym)

                # Check if the member already has an active visit
                active_visit = Visit.objects.filter(member=member, exit_time__isnull=True).first()
                if active_visit:
                    # Log the exit for the active visit
                    active_visit.exit_time = now()
                    active_visit.has_exit = True
                    active_visit.save()
                    messages.success(request, f"Goodbye {member.user.username}, you are signed out!")
                else:
                    # Create a new visit entry
                    Visit.objects.create(member=member, gym_code=gym_code)
                    messages.success(request, f"Welcome {member.user.username}, you are signed in!")
            except Member.DoesNotExist:
                messages.error(request, "Invalid gym code or you are not associated with this gym.")
        else:
            messages.error(request, "Form submission error.")
    else:
        form = GymCodeForm()

    return render(request, 'gym_checkin.html', {'form': form, 'gym': gym})

