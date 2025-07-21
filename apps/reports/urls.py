from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('users/', views.UserReportView.as_view(), name='user-report'),
    path('sections/', views.SectionReportView.as_view(), name='section-report'),
    path('assignments/', views.AssignmentReportView.as_view(), name='assignment-report'),
    path('grades/', views.SubmissionReportView.as_view(), name='submission-report'),
    path('enrollments/', views.EnrollmentReportView.as_view(), name='enrollment-report'),
    path('system/', views.system_report_view, name='system-report'),
]