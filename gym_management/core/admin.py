from django.contrib import admin
from .models import GymOwner, Gym, Member, Visit

admin.site.register(GymOwner)
admin.site.register(Gym)
admin.site.register(Member)
admin.site.register(Visit)