from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import GymOwner, Member, Visit, Gym
from .forms import GymCodeForm, MemberUpdateForm
from django.utils.timezone import now
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth import update_session_auth_hash


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
            slug = gym.slug
            gym_data.append({
                'gym_name': gym.name,
                'member_count': member_count,
                'gym_slug': slug
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

        # Get number of visits and average session time
        number_of_visits = Visit.get_number_of_visits(member)
        average_session_time = Visit.get_average_session_time(member)
        recent_visits = Visit.objects.filter(member=member).order_by('-entry_time')[:5]

        for visit in recent_visits:
            if visit.exit_time:
                visit.session_duration = round(((visit.exit_time - visit.entry_time).total_seconds() / 60), 2)  # in minutes
            else:
                visit.session_duration = '--'

        context = {
            'role': 'Member',
            'gym_name': member.gym.name,
            'join_date': member.join_date,
            'member_code': member.gym_code if member.gym_code else "No code assigned",
            'member_name': user.get_full_name().capitalize() or user.username.capitalize(),
            'number_of_visits': number_of_visits,
            'average_session_time': average_session_time,
            'recent_visits': recent_visits,
        }
        return render(request, 'member_dashboard.html', context)
    except Member.DoesNotExist:
        messages.error(request, "No member profile found.")
        return redirect('login')


# Gym checkin View (the render for the check-in page for each gym)
def gym_checkin_view(request, slug):
    # Fetch gym by its slug
    gym = get_object_or_404(Gym, slug=slug)

    # Check if logged in user is not the gym owner
    if not gym.owners.filter(user=request.user).exists():
        messages.error(request, "You are not authorized to access the check in page to this gym.")
        return redirect('login')

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



# Gym Dashboard Page
@login_required
def gym_dashboard(request, slug):
    # Fetch gym by its slug
    user = request.user
    gym = get_object_or_404(Gym, slug=slug)
    # Check if logged in user is not the gym owner
    try:
        # Fetch the gym owner object
        gym_owner = GymOwner.objects.get(user=user)
        if gym not in gym_owner.gyms.all():
            messages.error(request, "You are not authorized to access this gym's dashboard.")
            return redirect('login')
    # If it fails
    except GymOwner.DoesNotExist:
        messages.error(request, "You are not authorized to access the dashboard of this gym.")
        return redirect('login')

    # Metrics for Gym Dashboard
    member_count = gym.members.count()
    total_visits = Visit.get_number_of_visits_per_gym(gym)
    today_visits = Visit.objects.filter(member__gym=gym, entry_time__date=timezone.now().date()).count()
    avg_session_time = Visit.get_average_session_time_per_gym(gym) 

    top_visitors = (
        Visit.objects.filter(member__gym=gym, exit_time__isnull=False)
        .values('member__user__username', 'member__gym_code') 
        .annotate(visit_count=Count('id'))  
        .order_by('-visit_count')  
        )[:5]  


    context = {
        'gym_name': gym.name,
        'member_count': member_count,
        'total_visits': total_visits,
        'today_visits': today_visits,
        'avg_session_time': avg_session_time,
        'top_visitors': top_visitors,
    }
    
    return render(request, 'gym_dashboard.html', context)  



# Member details update form
@login_required
def member_update_view(request):
    user = request.user
    try:
        member = Member.objects.get(user=user)
    except Member.DoesNotExist:
        messages.error(request, "No member profile found.")
        return redirect('member_dashboard')

    # Initialise forms
    profile_form = MemberUpdateForm(instance=member, user=user)
    password_form = PasswordChangeForm(user=user)

    if request.method == "POST":
        if 'profile_submit' in request.POST:  # Profile form submission
            profile_form = MemberUpdateForm(request.POST, instance=member, user=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile has been updated successfully.")
                return redirect('member_update_view')
            else:
                messages.error(request, "Please correct the errors in the profile form.")

        elif 'password_submit' in request.POST:  # Password form submission
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, "Your password has been updated successfully.")
                return redirect('member_update_view')
            else:
                messages.error(request, "Please correct the errors in the password form.")

    return render(request, 'member_update.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })
