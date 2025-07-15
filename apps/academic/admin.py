from django.contrib import admin
from .models import Subject, Section, Enrollment, Assignment, Submission

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject_code', 'subject_name', 'school', 'created_at']
    list_filter = ['school', 'created_at']
    search_fields = ['subject_code', 'subject_name']
    ordering = ['subject_code']

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['section_name', 'subject', 'professor', 'school', 'start_date', 'end_date']
    list_filter = ['school', 'subject', 'start_date']
    search_fields = ['section_name', 'subject__subject_name', 'professor__username']
    ordering = ['-start_date']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'section', 'status', 'grade', 'enrollment_date']
    list_filter = ['status', 'school', 'enrollment_date']
    search_fields = ['student__username', 'section__section_name']
    ordering = ['-enrollment_date']

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'due_date', 'total_points', 'created_by']
    list_filter = ['school', 'due_date', 'created_at']
    search_fields = ['title', 'section__section_name']
    ordering = ['-due_date']

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'status', 'points_earned', 'submitted_at']
    list_filter = ['status', 'school', 'submitted_at']
    search_fields = ['student__username', 'assignment__title']
    ordering = ['-submitted_at']