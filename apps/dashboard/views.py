from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from apps.permissions import IsSuperAdmin, IsSchoolAdmin, IsProfessor, IsStudent
from apps.organizations.models import School, Subscription
from apps.users.models import User
from apps.academic.models import Subject, Section, Assignment, Submission, Enrollment
from .system_monitor import SystemMonitor
from .serializers import (
    SuperAdminDashboardSerializer,
    AdminDashboardSerializer, 
    ProfessorDashboardSerializer,
    StudentDashboardSerializer
)


class SuperAdminDashboardView(APIView):
    """Dashboard data for superadmin users"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        # Basic stats
        total_schools = School.objects.count()
        active_schools = School.objects.filter(is_active=True).count()
        total_users = User.objects.exclude(role='SUPERADMIN').count()
        active_subscriptions = Subscription.objects.filter(status='active').count()
        
        # Revenue calculation (mock data for now)
        revenue_this_month = Decimal('15000.00')
        growth_rate = 8.5
        
        # Recent schools
        recent_schools = School.objects.order_by('-created_at')[:5].values(
            'id', 'name', 'subdomain', 'created_at'
        )
        for school in recent_schools:
            school['user_count'] = User.objects.filter(school_id=school['id']).count()
            try:
                subscription = Subscription.objects.get(school_id=school['id'])
                school['subscription_status'] = subscription.status
            except Subscription.DoesNotExist:
                school['subscription_status'] = 'inactive'
        
        # Subscription overview
        subscription_overview = [
            {'plan': 'Basic', 'count': 15, 'revenue': 7500.00},
            {'plan': 'Premium', 'count': 8, 'revenue': 12000.00},
        ]
        
        # User growth (mock data)
        user_growth = []
        base_date = timezone.now() - timedelta(days=30)
        for i in range(30):
            date = base_date + timedelta(days=i)
            user_growth.append({
                'date': date.strftime('%Y-%m-%d'),
                'new_users': 2 + (i % 5),
                'total_users': total_users + i * 2
            })
        
        # System health
        system_health = SystemMonitor.get_system_health()
        
        data = {
            'stats': {
                'total_schools': total_schools,
                'active_schools': active_schools,
                'total_users': total_users,
                'active_subscriptions': active_subscriptions,
                'revenue_this_month': revenue_this_month,
                'growth_rate': growth_rate,
            },
            'recent_schools': list(recent_schools),
            'subscription_overview': subscription_overview,
            'user_growth': user_growth,
            'system_health': system_health,
        }
        
        return Response(data)


class AdminDashboardView(APIView):
    """Dashboard data for school admin users"""
    permission_classes = [IsAuthenticated, IsSchoolAdmin]
    
    def get(self, request):
        school = request.user.school
        
        # Basic stats
        total_users = User.objects.filter(school=school).exclude(role='SUPERADMIN').count()
        active_users = User.objects.filter(school=school, is_active=True).exclude(role='SUPERADMIN').count()
        total_sections = Section.objects.filter(school=school).count()
        total_assignments = Assignment.objects.filter(section__school=school).count()
        pending_submissions = Submission.objects.filter(
            assignment__section__school=school,
            grade__isnull=True
        ).count()
        
        avg_grade = Submission.objects.filter(
            assignment__section__school=school,
            grade__isnull=False
        ).aggregate(avg=Avg('grade'))['avg'] or 0.0
        
        # Recent users
        recent_users = User.objects.filter(school=school).order_by('-date_joined')[:10].values(
            'id', 'first_name', 'last_name', 'email', 'role', 'date_joined', 'is_active'
        )
        
        # Section overview
        section_overview = []
        sections = Section.objects.filter(school=school).select_related('subject', 'professor')[:10]
        for section in sections:
            student_count = Enrollment.objects.filter(section=section).count()
            assignment_count = Assignment.objects.filter(section=section).count()
            avg_grade = Submission.objects.filter(
                assignment__section=section,
                grade__isnull=False
            ).aggregate(avg=Avg('grade'))['avg'] or 0.0
            
            section_overview.append({
                'id': section.id,
                'section_name': section.name,
                'subject_name': section.subject.name,
                'professor_name': f"{section.professor.first_name} {section.professor.last_name}",
                'student_count': student_count,
                'assignment_count': assignment_count,
                'avg_grade': round(avg_grade, 2),
            })
        
        # Assignment stats (mock data)
        assignment_stats = [
            {'assignment_type': 'Homework', 'count': 45, 'avg_grade': 85.2, 'completion_rate': 92.0},
            {'assignment_type': 'Exam', 'count': 12, 'avg_grade': 78.5, 'completion_rate': 98.0},
            {'assignment_type': 'Project', 'count': 8, 'avg_grade': 88.1, 'completion_rate': 89.0},
        ]
        
        # User activity (mock data)
        user_activity = []
        base_date = timezone.now() - timedelta(days=7)
        for i in range(7):
            date = base_date + timedelta(days=i)
            user_activity.append({
                'date': date.strftime('%Y-%m-%d'),
                'logins': 25 + (i % 10),
                'submissions': 15 + (i % 8),
                'assignments_created': 2 + (i % 3),
            })
        
        data = {
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'total_sections': total_sections,
                'total_assignments': total_assignments,
                'pending_submissions': pending_submissions,
                'average_grade': round(avg_grade, 2),
            },
            'recent_users': list(recent_users),
            'section_overview': section_overview,
            'assignment_stats': assignment_stats,
            'user_activity': user_activity,
        }
        
        return Response(data)


class ProfessorDashboardView(APIView):
    """Dashboard data for professor users"""
    permission_classes = [IsAuthenticated, IsProfessor]
    
    def get(self, request):
        professor = request.user
        
        # Get professor's sections
        my_sections_qs = Section.objects.filter(professor=professor)
        my_sections_count = my_sections_qs.count()
        
        # Basic stats
        total_students = Enrollment.objects.filter(section__professor=professor).count()
        total_assignments = Assignment.objects.filter(section__professor=professor).count()
        pending_grading = Submission.objects.filter(
            assignment__section__professor=professor,
            grade__isnull=True
        ).count()
        
        avg_grade = Submission.objects.filter(
            assignment__section__professor=professor,
            grade__isnull=False
        ).aggregate(avg=Avg('grade'))['avg'] or 0.0
        
        late_submissions = Submission.objects.filter(
            assignment__section__professor=professor,
            submitted_at__gt=F('assignment__due_date')
        ).count()
        
        # My sections details
        my_sections = []
        for section in my_sections_qs:
            student_count = Enrollment.objects.filter(section=section).count()
            assignment_count = Assignment.objects.filter(section=section).count()
            pending_submissions = Submission.objects.filter(
                assignment__section=section,
                grade__isnull=True
            ).count()
            section_avg_grade = Submission.objects.filter(
                assignment__section=section,
                grade__isnull=False
            ).aggregate(avg=Avg('grade'))['avg'] or 0.0
            
            # Next assignment due
            next_assignment = Assignment.objects.filter(
                section=section,
                due_date__gt=timezone.now()
            ).order_by('due_date').first()
            
            my_sections.append({
                'id': section.id,
                'section_name': section.name,
                'subject_name': section.subject.name,
                'student_count': student_count,
                'assignment_count': assignment_count,
                'pending_submissions': pending_submissions,
                'avg_grade': round(section_avg_grade, 2),
                'next_assignment_due': next_assignment.due_date.isoformat() if next_assignment else None,
            })
        
        # Recent submissions
        recent_submissions = Submission.objects.filter(
            assignment__section__professor=professor
        ).select_related('student', 'assignment').order_by('-submitted_at')[:10]
        
        recent_submissions_data = []
        for submission in recent_submissions:
            recent_submissions_data.append({
                'id': submission.id,
                'student_name': f"{submission.student.first_name} {submission.student.last_name}",
                'assignment_title': submission.assignment.title,
                'section_name': submission.assignment.section.name,
                'submitted_at': submission.submitted_at.isoformat(),
                'is_late': submission.submitted_at > submission.assignment.due_date,
                'needs_grading': submission.grade is None,
            })
        
        # Assignment performance (mock data)
        assignment_performance = [
            {'assignment_title': 'Midterm Exam', 'avg_grade': 82.5, 'completion_rate': 95.0, 'late_rate': 5.0},
            {'assignment_title': 'Lab Report 3', 'avg_grade': 88.2, 'completion_rate': 90.0, 'late_rate': 10.0},
        ]
        
        # Upcoming deadlines
        upcoming_assignments = Assignment.objects.filter(
            section__professor=professor,
            due_date__gt=timezone.now()
        ).order_by('due_date')[:5]
        
        upcoming_deadlines = []
        for assignment in upcoming_assignments:
            submission_count = Submission.objects.filter(assignment=assignment).count()
            total_students = Enrollment.objects.filter(section=assignment.section).count()
            
            upcoming_deadlines.append({
                'assignment_title': assignment.title,
                'section_name': assignment.section.name,
                'due_date': assignment.due_date.isoformat(),
                'submission_count': submission_count,
                'total_students': total_students,
            })
        
        # Grade distribution (mock data)
        grade_distribution = [
            {'range': 'A (90-100)', 'count': 25, 'percentage': 30.0},
            {'range': 'B (80-89)', 'count': 35, 'percentage': 42.0},
            {'range': 'C (70-79)', 'count': 18, 'percentage': 22.0},
            {'range': 'D (60-69)', 'count': 4, 'percentage': 5.0},
            {'range': 'F (0-59)', 'count': 1, 'percentage': 1.0},
        ]
        
        data = {
            'stats': {
                'my_sections': my_sections_count,
                'total_students': total_students,
                'total_assignments': total_assignments,
                'pending_grading': pending_grading,
                'average_class_grade': round(avg_grade, 2),
                'late_submissions': late_submissions,
            },
            'my_sections': my_sections,
            'recent_submissions': recent_submissions_data,
            'assignment_performance': assignment_performance,
            'upcoming_deadlines': upcoming_deadlines,
            'grade_distribution': grade_distribution,
        }
        
        return Response(data)


class StudentDashboardView(APIView):
    """Dashboard data for student users"""
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get(self, request):
        student = request.user
        
        # Get student's enrollments
        enrollments = Enrollment.objects.filter(student=student).select_related('section__subject')
        enrolled_sections_count = enrollments.count()
        
        # Basic stats
        total_assignments = Assignment.objects.filter(
            section__enrollment__student=student
        ).count()
        
        completed_assignments = Submission.objects.filter(
            student=student
        ).count()
        
        pending_assignments = total_assignments - completed_assignments
        
        avg_grade = Submission.objects.filter(
            student=student,
            grade__isnull=False
        ).aggregate(avg=Avg('grade'))['avg'] or 0.0
        
        # GPA calculation (simplified)
        gpa = avg_grade / 25.0 if avg_grade else 0.0  # Convert to 4.0 scale
        
        # Enrolled sections
        enrolled_sections = []
        for enrollment in enrollments:
            section = enrollment.section
            assignment_count = Assignment.objects.filter(section=section).count()
            student_avg = Submission.objects.filter(
                student=student,
                assignment__section=section,
                grade__isnull=False
            ).aggregate(avg=Avg('grade'))['avg'] or 0.0
            
            # Next assignment due
            next_assignment = Assignment.objects.filter(
                section=section,
                due_date__gt=timezone.now()
            ).order_by('due_date').first()
            
            enrolled_sections.append({
                'id': section.id,
                'section_name': section.name,
                'subject_name': section.subject.name,
                'subject_code': section.subject.code,
                'professor_name': f"{section.professor.first_name} {section.professor.last_name}",
                'current_grade': round(student_avg, 2),
                'assignment_count': assignment_count,
                'next_assignment_due': next_assignment.due_date.isoformat() if next_assignment else None,
            })
        
        # Recent assignments
        recent_assignments_qs = Assignment.objects.filter(
            section__enrollment__student=student
        ).order_by('-created_at')[:10]
        
        recent_assignments = []
        for assignment in recent_assignments_qs:
            try:
                submission = Submission.objects.get(student=student, assignment=assignment)
                status = 'graded' if submission.grade is not None else 'submitted'
                grade = submission.grade
                is_late = submission.submitted_at > assignment.due_date
            except Submission.DoesNotExist:
                if assignment.due_date < timezone.now():
                    status = 'overdue'
                else:
                    status = 'pending'
                grade = None
                is_late = False
            
            recent_assignments.append({
                'id': assignment.id,
                'title': assignment.title,
                'subject_name': assignment.section.subject.name,
                'due_date': assignment.due_date.isoformat(),
                'status': status,
                'grade': grade,
                'max_points': assignment.max_points,
                'is_late': is_late,
            })
        
        # Upcoming deadlines
        upcoming_assignments = Assignment.objects.filter(
            section__enrollment__student=student,
            due_date__gt=timezone.now()
        ).order_by('due_date')[:5]
        
        upcoming_deadlines = []
        for assignment in upcoming_assignments:
            hours_remaining = (assignment.due_date - timezone.now()).total_seconds() / 3600
            
            upcoming_deadlines.append({
                'id': assignment.id,
                'title': assignment.title,
                'section_name': assignment.section.name,
                'due_date': assignment.due_date.isoformat(),
                'max_points': assignment.max_points,
                'hours_remaining': round(hours_remaining, 1),
            })
        
        # Grade trends
        submissions = Submission.objects.filter(
            student=student,
            grade__isnull=False
        ).select_related('assignment').order_by('submitted_at')[:10]
        
        grade_trends = []
        for submission in submissions:
            grade_trends.append({
                'assignment_title': submission.assignment.title,
                'grade': submission.grade,
                'max_points': submission.assignment.max_points,
                'submitted_at': submission.submitted_at.isoformat(),
            })
        
        # Performance by subject (mock data)
        performance_by_subject = [
            {'subject_name': 'Mathematics', 'avg_grade': 88.5, 'assignment_count': 8, 'completion_rate': 100.0},
            {'subject_name': 'Science', 'avg_grade': 82.3, 'assignment_count': 6, 'completion_rate': 95.0},
        ]
        
        data = {
            'stats': {
                'enrolled_sections': enrolled_sections_count,
                'total_assignments': total_assignments,
                'completed_assignments': completed_assignments,
                'pending_assignments': pending_assignments,
                'average_grade': round(avg_grade, 2),
                'gpa': round(gpa, 2),
            },
            'enrolled_sections': enrolled_sections,
            'recent_assignments': recent_assignments,
            'upcoming_deadlines': upcoming_deadlines,
            'grade_trends': grade_trends,
            'performance_by_subject': performance_by_subject,
        }
        
        return Response(data)


class QuickStatsView(APIView):
    """Quick stats for any authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Basic quick stats
        notifications = 5  # Mock data
        pending_tasks = 3  # Mock data
        recent_activity = "Last login: 2 hours ago"  # Mock data
        
        data = {
            'notifications': notifications,
            'pending_tasks': pending_tasks,
            'recent_activity': recent_activity,
        }
        
        return Response(data)


class SystemHealthView(APIView):
    """Real-time system health metrics"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        health_data = SystemMonitor.get_system_health()
        return Response(health_data)