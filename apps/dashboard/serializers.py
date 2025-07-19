from rest_framework import serializers


class SuperAdminStatsSerializer(serializers.Serializer):
    total_schools = serializers.IntegerField()
    active_schools = serializers.IntegerField()
    total_users = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()
    revenue_this_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    growth_rate = serializers.FloatField()


class SystemHealthSerializer(serializers.Serializer):
    database_status = serializers.ChoiceField(choices=['healthy', 'warning', 'critical', 'error'])
    api_response_time = serializers.FloatField()
    active_connections = serializers.IntegerField()
    memory_usage = serializers.FloatField()
    cpu_usage = serializers.FloatField()
    disk_usage = serializers.FloatField()
    overall_status = serializers.ChoiceField(choices=['healthy', 'warning', 'critical'])
    system_load = serializers.DictField()


class SuperAdminDashboardSerializer(serializers.Serializer):
    stats = SuperAdminStatsSerializer()
    recent_schools = serializers.ListField()
    subscription_overview = serializers.ListField()
    user_growth = serializers.ListField()
    system_health = SystemHealthSerializer()


class AdminStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_sections = serializers.IntegerField()
    total_assignments = serializers.IntegerField()
    pending_submissions = serializers.IntegerField()
    average_grade = serializers.FloatField()


class AdminDashboardSerializer(serializers.Serializer):
    stats = AdminStatsSerializer()
    recent_users = serializers.ListField()
    section_overview = serializers.ListField()
    assignment_stats = serializers.ListField()
    user_activity = serializers.ListField()


class ProfessorStatsSerializer(serializers.Serializer):
    my_sections = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_assignments = serializers.IntegerField()
    pending_grading = serializers.IntegerField()
    average_class_grade = serializers.FloatField()
    late_submissions = serializers.IntegerField()


class ProfessorDashboardSerializer(serializers.Serializer):
    stats = ProfessorStatsSerializer()
    my_sections = serializers.ListField()
    recent_submissions = serializers.ListField()
    assignment_performance = serializers.ListField()
    upcoming_deadlines = serializers.ListField()
    grade_distribution = serializers.ListField()


class StudentStatsSerializer(serializers.Serializer):
    enrolled_sections = serializers.IntegerField()
    total_assignments = serializers.IntegerField()
    completed_assignments = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    average_grade = serializers.FloatField()
    gpa = serializers.FloatField()


class StudentDashboardSerializer(serializers.Serializer):
    stats = StudentStatsSerializer()
    enrolled_sections = serializers.ListField()
    recent_assignments = serializers.ListField()
    upcoming_deadlines = serializers.ListField()
    grade_trends = serializers.ListField()
    performance_by_subject = serializers.ListField()