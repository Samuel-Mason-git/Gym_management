from django.contrib.auth.models import User
from django.db import models
from datetime import timedelta
from django.utils import timezone
import random as rd
from django.utils.text import slugify
from django.utils.timezone import now
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError


# Model to represent Gym Owners
class GymOwner(models.Model):
    # Link to Django's User model for authentication and login
    user = models.OneToOneField(User, on_delete=models.CASCADE)  
    
    # Mandatory personal information
    contact_number = models.CharField(max_length=15)

    
    # Additional Optional personal information for the gym owner
    date_of_birth = models.DateField(null=True, blank=True)  
    address = models.TextField(blank=True, null=True) 

    # Auto Assigned
    join_date = models.DateField(auto_now_add=True)  # Automatically set when the owner is created

    def __str__(self):
        # Display the username of the gym owner
        return self.user.username


# Intermediate model to link Gym and GymOwner with roles
class GymOwnership(models.Model):
    GYM_ROLE_CHOICES = [
        ('primary', 'Primary Owner'),
        ('manager', 'Manager'),
    ]
    gym = models.ForeignKey('Gym', on_delete=models.CASCADE, related_name='ownerships')
    owner = models.ForeignKey(GymOwner, on_delete=models.CASCADE, related_name='gym_roles')
    role = models.CharField(max_length=20, choices=GYM_ROLE_CHOICES, default='manager')

    class Meta:
        unique_together = ('gym', 'owner')  # Prevent duplicate relationships for the same gym and owner

    def clean(self):
        """Custom validation logic."""
        if self.role == 'primary':
            existing_primary = GymOwnership.objects.filter(gym=self.gym, role='primary').exclude(id=self.id)
            if existing_primary.exists():
                raise ValidationError(
                    f"The gym '{self.gym.name}' already has a primary owner. "
                    "You cannot add another primary owner."
                )
        elif self.role == 'manager':
            # Limit the number of managers to 20
            manager_count = GymOwnership.objects.filter(gym=self.gym, role='manager').count()
            if manager_count >= 20:
                raise ValidationError(
                    f"The gym '{self.gym.name}' already has the maximum number of managers (20)."
                )

    def save(self, *args, **kwargs):
        # Call the clean method to validate the model instance
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.owner} - {self.gym} ({self.role})"
    
    

# Model to represent Gyms
class Gym(models.Model):
    # Primary key for the Gym (auto-incremented ID)
    gym_id = models.AutoField(primary_key=True)
    
    # Name of the gym
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    address = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=15, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    
    # Link to the GymOwner who owns this gym
    # A GymOwner can own multiple gyms (one-to-many relationship)
    owners = models.ManyToManyField(GymOwner, related_name='gyms')

    def save(self, *args, **kwargs):
        # Generate a slug from the gym name
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        # Display the name of the gym
        return self.name
    
    def get_primary_owner(self):
        # Return the primary owner of the gym
        return self.ownerships.filter(role='primary').first()

    def get_managers(self):
        # Return all managers of the gym
        return self.ownerships.filter(role='manager')


# Model to represent Gym Members
class Member(models.Model):
    # Link to Django's User model for authentication and login
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Link to the Gym this member is associated with
    # A member belongs to one gym (many-to-one relationship)
    gym = models.ForeignKey(Gym, on_delete=models.SET_NULL, related_name='members', null=True) # Null = True so if a gym is deleted the members are not lost
    
    # Mandatory personal information
    contact_number = models.CharField(max_length=15)

    # Optional personal information for the member
    date_of_birth = models.DateField(null=True, blank=True)  # Optional date of birth
    address = models.TextField(blank=True, null=True)  # Optional address field
    active = models.BooleanField(default=False) # To activate when a subscription is generated, default is not set
    join_date = models.DateField(auto_now_add=True)  # Automatically set when the member is created

    # Unique Gym Code for Sign in
    gym_code = models.CharField(max_length=6, unique=True, blank=True)
    def save(self, *args, **kwargs):
        # Check if code exists
        if not self.gym_code:
            self.gym_code = self.generate_unique_gym_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_unique_gym_code():
        # Function to create code
        while True:
            code = f"{rd.randint(100000, 999999)}"
            if not Member.objects.filter(gym_code=code).exists():
                return code

    def __str__(self):
        # Display the username of the member
        return self.user.username






# Model to represent visiting database
class Visit(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='visits')
    gym_code = models.CharField(max_length=6) # Users gym code
    entry_time = models.DateTimeField(auto_now_add=True) # Automatically set when the visit is created
    exit_time = models.DateTimeField(null=True, blank=True)

    # A flag to check if a user has entered code for exit
    has_exit = models.BooleanField(default=False)

    # Default average visit duration (1.2 hours)
    default_exit_duration = timedelta(hours=1, minutes=12)

    # The threshold duration to apply the default exit time if the user doesn't log their exit
    default_exit_threshold = timedelta(hours=4)

    def auto_exit(self):
        """Set exit_time automatically if overdue."""
        if not self.exit_time and not self.has_exit:
            elapsed_time = now() - self.entry_time
            if elapsed_time > self.default_exit_threshold:
                self.exit_time = self.entry_time + self.default_exit_duration
                self.has_exit = True
                self.save()

    @classmethod
    def get_number_of_visits(cls, member):
        """Calculate the number of visits a member has made (completed visits)."""
        return cls.objects.filter(member=member, exit_time__isnull=False).count()
    
    @classmethod
    def get_average_session_time(cls, member):
        """Calculate the average session time for a member."""
        visits = cls.objects.filter(member=member, exit_time__isnull=False)
        total_session_time = timedelta(seconds=0)
        valid_visits_count = 0

        for visit in visits:
            exit_time = visit.exit_time or (visit.entry_time + visit.default_exit_duration)
            total_session_time += (exit_time - visit.entry_time)
            valid_visits_count += 1

        if valid_visits_count > 0:
            # Calculate average session time (in minutes)
            average_session_time = total_session_time / valid_visits_count
            return round((average_session_time.total_seconds() / 60))  # Convert to minutes
        return 0  # No visits, return 0 minute
    

    @classmethod
    def get_number_of_visits_per_gym(cls, gym):
        """Calculate the number of visits a member has made (completed visits)."""
        return cls.objects.filter(member__gym=gym, exit_time__isnull=False).count()
    
    @classmethod
    def get_average_session_time_per_gym(cls, gym):
        """Calculate the average session time for a member."""
        visits = cls.objects.filter(member__gym=gym, exit_time__isnull=False)
        total_session_time = timedelta(seconds=0)
        valid_visits_count = 0

        for visit in visits:
            exit_time = visit.exit_time or (visit.entry_time + visit.default_exit_duration)
            total_session_time += (exit_time - visit.entry_time)
            valid_visits_count += 1

        if valid_visits_count > 0:
            # Calculate average session time (in minutes)
            average_session_time = total_session_time / valid_visits_count
            return round((average_session_time.total_seconds() / 60),2)  # Convert to minutes
        return 0  # No visits, return 0 minute