from django.contrib import admin
from .models import GymOwner, Gym, Member, Visit

class GymOwnerAdmin(admin.ModelAdmin):
    list_display = ['user', 'contact_number', 'join_date']

class GymAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'get_owners']  # Replace 'owners' with 'get_owners'
    search_fields = ['name']

    def get_owners(self, obj):
        """Get all owners for a gym as a comma-separated string."""
        return ", ".join([owner.user.username for owner in obj.owners.all()])
    get_owners.short_description = "Owners"  # Sets the column name in the admin panel

admin.site.register(GymOwner, GymOwnerAdmin)
admin.site.register(Gym, GymAdmin)
admin.site.register(Member)
admin.site.register(Visit)
