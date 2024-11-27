from django.contrib import admin
from .models import GymOwner, Gym, Member, Visit
from django.utils.timezone import now

# GymOwnerAdmin to display owner info
class GymOwnerAdmin(admin.ModelAdmin):
    list_display = ['user', 'contact_number', 'join_date']

# MemberInline for inline editing of members under Gym
class MemberInline(admin.TabularInline):
    model = Member
    extra = 0
    fields = ('user', 'gym_code', 'contact_number')  # Exclude 'join_date' if it shouldn't be editable in this form

# GymAdmin to display gyms and their owners
class GymAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'address', 'get_owners']
    search_fields = ['name']
    inlines = [MemberInline]

    def get_owners(self, obj):
        return ", ".join([owner.user.username for owner in obj.owners.all()])
    get_owners.short_description = "Owners"

# MemberAdmin to manage Member model
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'gym', 'gym_code', 'contact_number', 'join_date')  # Display join_date
    readonly_fields = ('join_date',)  # Make join_date read-only
    search_fields = ('user__username', 'gym__name', 'gym_code')
    list_filter = ('gym',)

# VisitAdmin to manage visits and mark them as completed
@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('member', 'gym_code', 'entry_time', 'exit_time', 'has_exit')
    list_filter = ('has_exit', 'gym_code')
    search_fields = ('member__user__username', 'gym_code')
    date_hierarchy = 'entry_time'
    readonly_fields = ('entry_time',)
    actions = ['mark_as_completed']

    def mark_as_completed(self, request, queryset):
        rows_updated = queryset.update(has_exit=True, exit_time=now())
        self.message_user(request, f"{rows_updated} visit(s) marked as completed.")
    mark_as_completed.short_description = "Mark selected visits as completed"

# Register models (Visit is already registered with @admin.register(Visit))
admin.site.register(GymOwner, GymOwnerAdmin)
admin.site.register(Gym, GymAdmin)
