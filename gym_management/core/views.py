from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import GymOwner, Member, Visit, Gym, GymOwnership, VerificationToken
from .forms import GymCodeForm, MemberUpdateForm, GymUpdateForm, ManagerRegistrationForm
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
import random
from django.urls import reverse
from datetime import timedelta

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
    # Check if the logged-in user is a gym owner or manager for this gym
    try:
        gym_ownership = GymOwnership.objects.filter(
            gym=gym,
            owner__user=user,
            role__in=['primary', 'manager']
        ).first()

        if not gym_ownership:
            messages.error(request, "You are not authorized to access this gym's dashboard.")
            return redirect('login')
    except GymOwnership.DoesNotExist:
        messages.error(request, "You are not authorized to access this gym's dashboard.")
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




@login_required
def invite_or_assign_manager(request, slug):
    gym = get_object_or_404(Gym, slug=slug)
    primary_owner = gym.ownerships.filter(role='primary', owner__user=request.user).first()
    # Initialize 
    subject = ''
    body = ''

    # Ensure the logged-in user is the primary owner
    if not primary_owner:
        messages.error(request, "You must be the primary owner to invite or assign a manager.")
        return redirect('gym_dashboard', slug=gym.slug)

    if request.method == 'POST':
        email = request.POST.get('email')

        if not email:
            messages.error(request, "Email is required to invite or assign a manager.")
            return redirect('gym_settings', slug=gym.slug)

        # Check if the user exists
        user = User.objects.filter(email=email).first()
        if user:
            # Check if they are already a manager
            existing_manager = gym.ownerships.filter(owner__user=user, role='manager').first()
            if existing_manager:
                messages.warning(request, "This user is already a manager for this gym.")
            else:
                # Ensure the user has a GymOwner instance
                gym_owner, created = GymOwner.objects.get_or_create(user=user)

                # Assign as manager and notify
                GymOwnership.objects.create(gym=gym, owner=gym_owner, role='manager')
                messages.success(request, f"{user.get_full_name()} has been added as a manager.")

                subject = "Added as a Manager for: {gym.name}"
                body = f"""
                <p>Dear {user.first_name},</p>
                <p>You have been added as a manager for the gym <strong>{gym.name}</strong>.</p>
                <p>You will now find the Gym's dashboard on your Gym Owners dashboard after login.</p>
                <p>Thank you,</p>
                <p>{settings.SITE_NAME} Team</p>
            """
            send_email(subject, body, [email], gym=gym)

        else:
            unique_token = random.randint(10000000,99999999)
            expiration_date = now() + timedelta(days=7)
            VerificationToken.objects.create(
                email=email,
                token=unique_token,
                gym=gym,
                expires_at=expiration_date
            )

            # Send invitation email
            subject = f"Invitation to Manage {gym.name} at {settings.SITE_NAME}"
            registration_url = f"{settings.SITE_URL}{reverse('register_manager')}"
            body = f"""
                <p>Dear User,</p>
                <p>You have been invited to become a manager for the gym <strong>{gym.name}</strong>.</p>
                <p>Your unique 8-digit verification code is: <strong>{unique_token}</strong>. HURRY! As this code will expire in 7 days.</p>
                <p>Please click the link below to register and accept your manager role:</p>
                <p><a href="{registration_url}">Accept Invitation</a></p>
                <p>Thank you,</p>
                <p>{settings.SITE_NAME} Team</p>
            """
            try:
                send_email(subject, body, [email], gym=gym)
                messages.success(request, "Invitation email has been sent successfully.")
            except Exception as e:
                messages.error(request, f"Failed to send email: {e}")

        return redirect('gym_settings', slug=gym.slug)

    return redirect('gym_settings', slug=gym.slug)




# A view to verify the code and email for an invite as a Gym Manager and add them
def register_manager(request):
    if request.method == "POST":
        form = ManagerRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            token = form.cleaned_data['token']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']

            # Validate the token
            try:
                verification_token = VerificationToken.objects.get(email=email, token=token)
                if verification_token.is_used:
                    messages.error(request, "This verification code has already been used.")
                    return render(request, 'register_manager.html', {'form': form})
                if verification_token.expires_at < now():
                    messages.error(request, "This verification code has expired.")
                    return render(request, 'register_manager.html', {'form': form})

                # Create the user
                user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
                
                # Ensure the user has a GymOwner instance
                gym_owner, created = GymOwner.objects.get_or_create(user=user)

                # Assign the user as a manager to the gym
                gym = verification_token.gym
                GymOwnership.objects.create(gym=gym, owner=gym_owner, role='manager')

                # Mark the token as used
                verification_token.is_used = True
                verification_token.save()

                messages.success(request, "Registration successful! You are now a manager.")
                return redirect('login')  # Redirect to login or dashboard
            except VerificationToken.DoesNotExist:
                messages.error(request, "Invalid email or verification code.")
        else:
            # Invalid form
            messages.error(request, "Please correct the errors below.")

    else:
        form = ManagerRegistrationForm()

    return render(request, 'register_manager.html', {'form': form})



# Button for a gym owner to delete a gym
@login_required
def delete_gym(request, slug):
    # Fetch the gym
    gym = get_object_or_404(Gym, slug=slug)

    # Ensure the logged-in user is the primary owner
    primary_owner = gym.ownerships.filter(role='primary', owner__user=request.user).first()
    if not primary_owner:
        messages.error(request, "You must be the primary owner to delete this gym.")
        return redirect('gym_dashboard', slug=gym.slug)

    if request.method == "POST":
        # Delete the gym and related ownerships
        gym.delete()
        messages.success(request, "Gym deleted successfully!")
        return redirect('gym_owner_dashboard')

    # Redirect back if the method is not POST
    return redirect('gym_settings', slug=slug)