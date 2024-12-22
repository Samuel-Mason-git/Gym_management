from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import GymOwner, Member, Visit, Gym, GymOwnership
from .forms import GymCodeForm, MemberUpdateForm, GymUpdateForm
from django.utils.timezone import now
from django.utils import timezone
from django.http import JsonResponse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.models import User
from django.db.models import Count
from django.contrib.auth import update_session_auth_hash
from core.emails import send_email
from django.conf import settings

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
        # Fetch the GymOwner profile for the logged-in user
        gym_owner = GymOwner.objects.get(user=user)

        # Query for gyms where the user is the primary owner
        primary_gyms = GymOwnership.objects.filter(owner=gym_owner, role='primary').select_related('gym')

        # Query for gyms where the user is a manager
        managed_gyms = GymOwnership.objects.filter(owner=gym_owner, role='manager').select_related('gym')

        # Prepare data for primary gyms
        primary_gym_data = []
        for ownership in primary_gyms:
            gym = ownership.gym
            primary_gym_data.append({
                'gym_name': gym.name,
                'member_count': gym.members.count(),
                'active_members': gym.members.filter(active=True).count(),
                'gym_slug': gym.slug,
            })

        # Prepare data for managed gyms
        managed_gym_data = []
        for ownership in managed_gyms:
            gym = ownership.gym
            managed_gym_data.append({
                'gym_name': gym.name,
                'member_count': gym.members.count(),
                'active_members': gym.members.filter(active=True).count(),
                'gym_slug': gym.slug,
            })

        context = {
            'role': 'Gym Owner',
            'gym_owner_name': gym_owner.user.get_full_name(),
            'primary_gyms': primary_gym_data,
            'managed_gyms': managed_gym_data,
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

                # Check if the member's subscription is active
                if not member.active:  
                    messages.error(request, f"Your subscription is inactive {member.user.first_name}, you cant Check-in right now.")
                    return redirect('gym_checkin', slug=slug)

                # Check if the member already has an active visit
                active_visit = Visit.objects.filter(member=member, exit_time__isnull=True).first()
                if active_visit:
                    # Log the exit for the active visit
                    active_visit.exit_time = now()
                    active_visit.has_exit = True
                    active_visit.save()
                    messages.success(request, f"Goodbye {member.user.first_name}, you are signed out!")
                else:
                    # Create a new visit entry
                    Visit.objects.create(member=member, gym_code=gym_code)
                    messages.success(request, f"Welcome {member.user.first_name}, you are signed in!")
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
            messages.error(request, "You are not authorised to access this gym's dashboard.")
            return redirect('login')
    # If it fails
    except GymOwner.DoesNotExist:
        messages.error(request, "You are not authorised to access the dashboard of this gym.")
        return redirect('login')

    # Metrics for Gym Dashboard

    is_admin = gym.ownerships.filter(owner__user=user, role='primary').exists()
    member_count = gym.members.count()
    active_members_count = Member.objects.filter(gym=gym, active=True).count()
    inactive_members_count = Member.objects.filter(gym=gym, active=False).count()

    total_visits = Visit.get_number_of_visits_per_gym(gym)
    today_visits = Visit.objects.filter(member__gym=gym, entry_time__date=timezone.now().date()).count()
    avg_session_time = Visit.get_average_session_time_per_gym(gym) 

    top_visitors = (
        Visit.objects.filter(member__gym=gym, exit_time__isnull=False)
        .values('member__user__username', 'member__gym_code') 
        .annotate(visit_count=Count('id'))  
        .order_by('-visit_count')  
        )[:10]  
    
    recent_visits = (
        Visit.objects.filter(member__gym=gym, exit_time__isnull=False)  
        .order_by('-entry_time')  
        )[:10]  

    for visit in recent_visits:
        if visit.exit_time:
            session_duration = visit.exit_time - visit.entry_time
            visit.session_duration = round(session_duration.total_seconds() / 60, 2) 
        else:
            visit.session_duration = 0 

    context = {
        'gym_name': gym.name,
        'member_count': member_count,
        'total_visits': total_visits,
        'today_visits': today_visits,
        'avg_session_time': avg_session_time,
        'top_visitors': top_visitors,
        'gym_slug': slug,
        'recent_visits': recent_visits,
        'active_members': active_members_count,
        'inactive_members': inactive_members_count,
        'is_admin': is_admin,
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




# Member details update form
@login_required
def gym_owner_update_view(request):
    user = request.user
    try:
        gym_owner = GymOwner.objects.get(user=user)
    except GymOwner.DoesNotExist:
        messages.error(request, "No Gym Owner profile found.")
        return redirect('gym_owner_dashboard')

    # Initialise forms
    profile_form = MemberUpdateForm(instance=gym_owner, user=user)
    password_form = PasswordChangeForm(user=user)

    if request.method == "POST":
        if 'profile_submit' in request.POST:  # Profile form submission
            profile_form = MemberUpdateForm(request.POST, instance=gym_owner, user=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile has been updated successfully.")
                return redirect('gym_owner_update_view')
            else:
                messages.error(request, "Please correct the errors in the profile form.")

        elif 'password_submit' in request.POST:  # Password form submission
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, "Your password has been updated successfully.")
                return redirect('gym_owner_update_view')
            else:
                messages.error(request, "Please correct the errors in the password form.")

    return render(request, 'gym_owner_update.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from .models import Gym, GymOwnership
from .forms import GymUpdateForm

@login_required
def gym_settings(request, slug):
    # Ensure the gym exists and the logged-in user is the primary owner
    gym = get_object_or_404(Gym, slug=slug)
    primary_owner = gym.ownerships.filter(role='primary', owner__user=request.user).first()

    # If the user is not the primary owner, redirect them or show an error
    if not primary_owner:
        messages.error(request, "You must be the primary owner to access the settings.")
        return redirect('gym_dashboard', slug=gym.slug)

    # Get all gym ownership relationships for this gym
    gym_ownerships = gym.ownerships.select_related('owner').all()

    # Filter primary owners and managers
    primary_owners = gym_ownerships.filter(role='primary')
    managers = gym_ownerships.filter(role='manager')
    number_of_managers = managers.count()

    # Total admins = primary owners + managers
    total_admins = managers.count()

    if request.method == 'POST':
        # Handle the gym basic information update form
        form = GymUpdateForm(request.POST, instance=gym)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gym information updated successfully!')
            return redirect('gym_settings', slug=slug)
        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = GymUpdateForm(instance=gym)

    return render(request, 'gym_settings.html', {
        'form': form,
        'gym': gym,
        'gym_slug': slug,
        'primary_owners': primary_owners,
        'managers': managers,
        'total_gym_admins': total_admins,
        'is_admin': True,
    })



@login_required
def remove_manager(request, slug, manager_id):
    gym = get_object_or_404(Gym, slug=slug)
    primary_owner = gym.ownerships.filter(role='primary', owner__user=request.user).first()

    # Ensure the logged-in user is the primary owner
    if not primary_owner:
        messages.error(request, "You must be the primary owner to remove a manager.")
        return redirect('gym_dashboard', slug=gym.slug)

    # Get the manager object and remove the ownership relation
    manager_ownership = gym.ownerships.filter(owner__id=manager_id, role='manager').first()

    if manager_ownership:
        manager_ownership.delete()
        messages.success(request, "Manager removed successfully.")
    else:
        messages.error(request, "Manager not found.")

    return redirect('gym_settings', slug=slug)