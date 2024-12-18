from django.contrib import admin
from .models import GymOwner, GymOwnership, Gym, Member, Visit

# Admin configuration for GymOwner
@admin.register(GymOwner)
class GymOwnerAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'email', 'contact_number', 'join_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'contact_number')
    ordering = ('join_date',)

    # Helper methods to display related fields
    @admin.display(description="First Name")
    def first_name(self, obj):
        return obj.user.first_name

    @admin.display(description="Last Name")
    def last_name(self, obj):
        return obj.user.last_name

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email

# Inline admin for GymOwnership (to manage ownerships directly from the Gym admin)
class GymOwnershipInline(admin.TabularInline):
    model = GymOwnership
    extra = 1  # Number of extra empty forms to display
    autocomplete_fields = ['owner']  # Searchable dropdown for owners
    fields = ('owner', 'role')

# Admin configuration for Gym
@admin.register(Gym)
class GymAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'contact_number', 'email', 'get_primary_owner')
    search_fields = ('name', 'contact_number', 'email')
    inlines = [GymOwnershipInline]
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    def get_primary_owner(self, obj):
        primary_owner = obj.get_primary_owner()
        return primary_owner.owner.user.username if primary_owner else "No Primary Owner"
    get_primary_owner.short_description = "Primary Owner"

# Admin configuration for GymOwnership
@admin.register(GymOwnership)
class GymOwnershipAdmin(admin.ModelAdmin):
    list_display = ('gym', 'owner', 'role')
    search_fields = ('gym__name', 'owner__user__username')
    list_filter = ('role',)

# Admin configuration for Member
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'gym', 'contact_number', 'active', 'join_date')
    search_fields = ('user__username', 'contact_number', 'gym__name')
    list_filter = ('active', 'join_date')
    ordering = ('join_date',)

# Admin configuration for Visit
@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('member', 'gym_code', 'entry_time', 'exit_time', 'has_exit')
    search_fields = ('member__user__username', 'gym_code')
    list_filter = ('entry_time', 'has_exit')
    ordering = ('entry_time',)
