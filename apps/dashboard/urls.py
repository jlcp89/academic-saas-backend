from django.urls import path
from .views import (
    SuperAdminDashboardView,
    AdminDashboardView,
    ProfessorDashboardView,
    StudentDashboardView,
    QuickStatsView,
    SystemHealthView,
)

urlpatterns = [
    path('superadmin/', SuperAdminDashboardView.as_view(), name='superadmin-dashboard'),
    path('admin/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('professor/', ProfessorDashboardView.as_view(), name='professor-dashboard'),
    path('student/', StudentDashboardView.as_view(), name='student-dashboard'),
    path('quick-stats/', QuickStatsView.as_view(), name='quick-stats'),
    path('system_health/', SystemHealthView.as_view(), name='system-health'),
]