from django.contrib.auth.models import User
from django.db import models
from datetime import timedelta
from django.utils import timezone
import random as rd


# Model to represent Gym Owners
class GymOwner(models.Model):
    # Link to Django's User model for authentication and login
    user = models.OneToOneField(User, on_delete=models.CASCADE)  
    
    # Mandatory personal information
    contact_number = models.CharField(max_length=15)


    # Additional Optional personal information for the gym owner
    date_of_birth = models.DateField(null=True, blank=True)  
    address = models.TextField(blank=True, null=True) 

    join_date = models.DateField(auto_now_add=True)  # Automatically set when the owner is created

    def __str__(self):
        # Display the username of the gym owner
        return self.user.username




# Model to represent Gyms
class Gym(models.Model):
    # Primary key for the Gym (auto-incremented ID)
    gym_id = models.AutoField(primary_key=True)
    
    # Name of the gym
    name = models.CharField(max_length=255)
    
    # Link to the GymOwner who owns this gym
    # A GymOwner can own multiple gyms (one-to-many relationship)
    owner = models.ForeignKey(GymOwner, on_delete=models.CASCADE, related_name='gyms')
    
    def __str__(self):
        # Display the name of the gym
        return self.name





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
    default_exit_threshold = timedelta(hours=4, minutes=0)

    # Add in exit handinling with automated checks to see if a user has not signed out
