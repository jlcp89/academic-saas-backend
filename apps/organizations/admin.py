from django.contrib import admin
from .models import School, Subscription

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'subdomain', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'subdomain']
    ordering = ['-created_at']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['school', 'plan', 'status', 'end_date']
    list_filter = ['plan', 'status']
    search_fields = ['school__name']
    ordering = ['end_date']