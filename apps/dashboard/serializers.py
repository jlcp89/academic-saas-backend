from rest_framework import serializers
from apps.users.models import User
from apps.organizations.models import School


class SuperAdminDashboardSerializer(serializers.Serializer):
    """SuperAdmin dashboard data serializer"""
    stats = serializers.DictField()
    recent_schools = serializers.ListField()
    subscription_overview = serializers.ListField()
    user_growth = serializers.ListField()
    system_health = serializers.DictField()


class AdminDashboardSerializer(serializers.Serializer):
    """Admin dashboard data serializer"""
    stats = serializers.DictField()
    recent_users = serializers.ListField()
    section_overview = serializers.ListField()
    assignment_stats = serializers.ListField()
    user_activity = serializers.ListField()


class ProfessorDashboardSerializer(serializers.Serializer):
    """Professor dashboard data serializer"""
    stats = serializers.DictField()
    my_sections = serializers.ListField()
    recent_submissions = serializers.ListField()
    assignment_performance = serializers.ListField()
    upcoming_deadlines = serializers.ListField()
    grade_distribution = serializers.ListField()


class StudentDashboardSerializer(serializers.Serializer):
    """Student dashboard data serializer"""
    stats = serializers.DictField()
    enrolled_sections = serializers.ListField()
    recent_assignments = serializers.ListField()
    upcoming_deadlines = serializers.ListField()
    grade_trends = serializers.ListField()
    performance_by_subject = serializers.ListField()


class QuickStatsSerializer(serializers.Serializer):
    """Quick stats for all roles"""
    notifications = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    recent_activity = serializers.CharField()