from django.contrib.auth.models import User
from django.db import models
from datetime import timedelta
from django.utils import timezone
import random as rd
from django.utils.text import slugify
from django.utils.timezone import now
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError


class SubscriptionTier(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max_gyms = models.PositiveIntegerField(default=1)
    max_members = models.PositiveIntegerField(default=1000)
    max_regular_products = models.PositiveIntegerField(default=10)
    max_subscription_products = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.name


# Model to represent Gym Owners
class GymOwner(models.Model):
    # Link to Django's User model for authentication and login
    user = models.OneToOneField(User, on_delete=models.CASCADE)  
    contact_number = models.CharField(max_length=15)
    date_of_birth = models.DateField(null=True, blank=True)  
    address = models.TextField(blank=True, null=True) 
    join_date = models.DateField(auto_now_add=True)  

    # Subscription info for the gym owner
    subscription_tier = models.ForeignKey(SubscriptionTier, on_delete=models.SET_NULL, null=True)
    subscription_start_date = models.DateTimeField(null=True, blank=True)

    def get_usage_and_limit(self, resource: str) -> dict:
        if not self.subscription_tier:
            return {'current_usage': 0, 'max_limit': 0}  # No subscription means no access
    
        # Subscription-wide limits
        limits = {
            'gyms': self.subscription_tier.max_gyms,
            'members': self.subscription_tier.max_members,
        }
    
        # Current usage
        usage = {
            'gyms': self.gyms.filter(ownerships__role='primary').count(),  # Count only primary gyms
            'members': sum(gym.members.count() for gym in self.gyms.filter(ownerships__role='primary')),  # Count members in primary gyms only
        }
    
        return {
            'current_usage': usage.get(resource, 0),
            'max_limit': limits.get(resource, 0)
        }


    def __str__(self):
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
    email_domain = models.EmailField(blank=True, null=True) # Custom Email Domain to be added
    
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
        return 0  # No visits, return 0 minute]




# A Product table  with a foriegn key of gyms so each gym can offer its own products and we store them all in one big database
class Product(models.Model):
    stripe_product_id = models.CharField(max_length=255, unique=True)  # Stripe product ID
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='products')  # Link to the gym
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Local price
    stripe_price_id = models.CharField(max_length=255, unique=True)  # Stripe price ID
    active = models.BooleanField(default=True)  # Indicates whether the product is available
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.gym.name})"



# A subscription model table linking to each gym so we can see all subscribers, their status and then which gym they belong too
class Subscription(models.Model):
    stripe_subscription_id = models.CharField(max_length=255, unique=True)  # Stripe subscription ID
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='subscriptions')
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='subscriptions')  # Gym context
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='subscriptions')
    start_date = models.DateTimeField()  # Subscription start
    end_date = models.DateTimeField(null=True, blank=True)  # Optional end date
    status = models.CharField(
        max_length=50,
        choices=[
            ('active', 'Active'),
            ('canceled', 'Canceled'),
            ('past_due', 'Past Due'),
            ('unpaid', 'Unpaid'),
        ],
        default='active'
    )
    auto_renew = models.BooleanField(default=True)  # Automatically renew subscription
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - {self.product.name} ({self.status})"


# A orders table for all orders processed under the web application
class Order(models.Model):
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)  # Stripe payment intent ID
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='orders')
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='orders')  # Link to gym
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)  # Total amount
    status = models.CharField(
        max_length=50,
        choices=[
            ('succeeded', 'Succeeded'),
            ('failed', 'Failed'),
            ('pending', 'Pending'),
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} ({self.member.user.username}) - {self.status}"



# This is to store the verification tokens for gym manager invites
class VerificationToken(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=8, unique=True)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)