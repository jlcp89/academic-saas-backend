from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
import random
import time

from apps.users.models import User
from apps.organizations.models import School, Subscription
from apps.academic.models import Subject, Section, Assignment, Submission, Enrollment
from apps.permissions import IsSuperAdmin, IsSchoolAdmin, IsProfessor, IsStudent
from .system_monitor import SystemMonitor
from .serializers import (
    SuperAdminDashboardSerializer,
    AdminDashboardSerializer,
    ProfessorDashboardSerializer,
    StudentDashboardSerializer,
    QuickStatsSerializer
)


class DashboardViewSet(ViewSet):
    """Dashboard endpoints for different user roles"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated & IsSuperAdmin])
    def superadmin(self, request):
        """SuperAdmin dashboard data"""
        # Measure API response time for this entire operation
        start_time = time.time()
        
        now = timezone.now()
        this_month = now.month
        this_year = now.year
        
        # Basic stats
        total_schools = School.objects.count()
        active_schools = School.objects.filter(is_active=True).count()
        total_users = User.objects.exclude(role='SUPERADMIN').count()
        active_subscriptions = Subscription.objects.filter(status='ACTIVE').count()
        
        # Calculate monthly revenue (mock data for now)
        revenue_this_month = active_subscriptions * 100  # Basic plan price
        growth_rate = random.uniform(5, 15)  # Mock growth rate
        
        # Recent schools
        recent_schools = []
        for school in School.objects.all().order_by('-created_at')[:5]:
            user_count = User.objects.filter(school=school).count()
            subscription_status = getattr(school, 'subscription', None)
            recent_schools.append({
                'id': school.id,
                'name': school.name,
                'subdomain': school.subdomain,
                'created_at': school.created_at.isoformat(),
                'user_count': user_count,
                'subscription_status': subscription_status.status if subscription_status else 'INACTIVE'
            })
        
        # Subscription overview
        subscription_overview = []
        for plan in ['BASIC', 'PREMIUM']:
            count = Subscription.objects.filter(plan=plan, status='ACTIVE').count()
            revenue = count * (100 if plan == 'BASIC' else 200)
            subscription_overview.append({
                'plan': plan,
                'count': count,
                'revenue': revenue
            })
        
        # User growth trend (mock data)
        user_growth = []
        for i in range(7):
            date = now - timedelta(days=i)
            new_users = random.randint(5, 20)
            total_users_at_date = User.objects.filter(date_joined__date__lte=date.date()).count()
            user_growth.append({
                'date': date.date().isoformat(),
                'new_users': new_users,
                'total_users': total_users_at_date
            })
        user_growth.reverse()
        
        # Get real system health metrics
        health_metrics = SystemMonitor.get_cached_health()
        
        # Calculate API response time for this request
        api_response_time = round((time.time() - start_time) * 1000, 2)
        
        # System health with real metrics
        system_health = {
            'database_status': health_metrics['database_status'],
            'api_response_time': api_response_time,
            'active_connections': health_metrics['active_connections'],
            'memory_usage': health_metrics['memory_usage'],
            'cpu_usage': health_metrics['cpu_usage'],
            'disk_usage': health_metrics['disk_usage'],
            'overall_status': health_metrics['overall_status'],
            'system_load': health_metrics['system_load']
        }
        
        data = {
            'stats': {
                'total_schools': total_schools,
                'active_schools': active_schools,
                'total_users': total_users,
                'active_subscriptions': active_subscriptions,
                'revenue_this_month': revenue_this_month,
                'growth_rate': growth_rate
            },
            'recent_schools': recent_schools,
            'subscription_overview': subscription_overview,
            'user_growth': user_growth,
            'system_health': system_health
        }
        
        serializer = SuperAdminDashboardSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated & IsSchoolAdmin])
    def admin(self, request):
        """Admin dashboard data"""
        school = request.user.school
        
        # Basic stats
        total_users = User.objects.filter(school=school).exclude(role='SUPERADMIN').count()
        active_users = User.objects.filter(school=school, is_active=True).exclude(role='SUPERADMIN').count()
        total_sections = Section.objects.filter(school=school).count()
        total_assignments = Assignment.objects.filter(school=school).count()
        pending_submissions = Submission.objects.filter(
            school=school, 
            status='SUBMITTED'
        ).count()
        
        # Calculate average grade
        avg_grade = Submission.objects.filter(
            school=school, 
            points_earned__isnull=False
        ).aggregate(avg=Avg('points_earned'))['avg'] or 0
        
        # Recent users
        recent_users = []
        for user in User.objects.filter(school=school).order_by('-date_joined')[:10]:
            recent_users.append({
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role,
                'date_joined': user.date_joined.isoformat(),
                'is_active': user.is_active
            })
        
        # Section overview
        section_overview = []
        for section in Section.objects.filter(school=school).select_related('subject', 'professor')[:10]:
            student_count = Enrollment.objects.filter(section=section, status='ENROLLED').count()
            assignment_count = Assignment.objects.filter(section=section).count()
            avg_grade = Submission.objects.filter(
                assignment__section=section,
                points_earned__isnull=False
            ).aggregate(avg=Avg('points_earned'))['avg'] or 0
            
            section_overview.append({
                'id': section.id,
                'section_name': section.section_name,
                'subject_name': section.subject.subject_name,
                'professor_name': f"{section.professor.first_name} {section.professor.last_name}" if section.professor else 'No Professor',
                'student_count': student_count,
                'assignment_count': assignment_count,
                'avg_grade': float(avg_grade) if avg_grade else 0
            })
        
        # Assignment stats by type
        assignment_stats = []
        assignment_types = ['HOMEWORK', 'QUIZ', 'EXAM', 'PROJECT', 'DISCUSSION']
        for assignment_type in assignment_types:
            assignments = Assignment.objects.filter(school=school, title__icontains=assignment_type.lower())
            count = assignments.count()
            if count > 0:
                avg_grade = Submission.objects.filter(
                    assignment__in=assignments,
                    points_earned__isnull=False
                ).aggregate(avg=Avg('points_earned'))['avg'] or 0
                
                total_submissions = Submission.objects.filter(assignment__in=assignments).count()
                completed_submissions = Submission.objects.filter(
                    assignment__in=assignments,
                    status__in=['GRADED', 'RETURNED']
                ).count()
                completion_rate = (completed_submissions / total_submissions * 100) if total_submissions > 0 else 0
                
                assignment_stats.append({
                    'assignment_type': assignment_type,
                    'count': count,
                    'avg_grade': float(avg_grade) if avg_grade else 0,
                    'completion_rate': completion_rate
                })
        
        # User activity (mock data for now)
        user_activity = []
        for i in range(7):
            date = timezone.now() - timedelta(days=i)
            user_activity.append({
                'date': date.date().isoformat(),
                'logins': random.randint(10, 50),
                'submissions': random.randint(5, 25),
                'assignments_created': random.randint(1, 5)
            })
        user_activity.reverse()
        
        data = {
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'total_sections': total_sections,
                'total_assignments': total_assignments,
                'pending_submissions': pending_submissions,
                'average_grade': float(avg_grade) if avg_grade else 0
            },
            'recent_users': recent_users,
            'section_overview': section_overview,
            'assignment_stats': assignment_stats,
            'user_activity': user_activity
        }
        
        serializer = AdminDashboardSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated & IsProfessor])
    def professor(self, request):
        """Professor dashboard data"""
        professor = request.user
        school = professor.school
        
        # My sections
        my_sections = Section.objects.filter(school=school, professor=professor)
        
        # Basic stats
        total_students = Enrollment.objects.filter(
            section__in=my_sections,
            status='ENROLLED'
        ).count()
        total_assignments = Assignment.objects.filter(section__in=my_sections).count()
        pending_grading = Submission.objects.filter(
            assignment__section__in=my_sections,
            status='SUBMITTED'
        ).count()
        
        # Calculate average class grade
        avg_class_grade = Submission.objects.filter(
            assignment__section__in=my_sections,
            points_earned__isnull=False
        ).aggregate(avg=Avg('points_earned'))['avg'] or 0
        
        # Late submissions
        late_submissions = Submission.objects.filter(
            assignment__section__in=my_sections,
            submitted_at__gt=models.F('assignment__due_date')
        ).count()
        
        # My sections data
        my_sections_data = []
        for section in my_sections:
            student_count = Enrollment.objects.filter(section=section, status='ENROLLED').count()
            assignment_count = Assignment.objects.filter(section=section).count()
            pending_submissions = Submission.objects.filter(
                assignment__section=section,
                status='SUBMITTED'
            ).count()
            
            avg_grade = Submission.objects.filter(
                assignment__section=section,
                points_earned__isnull=False
            ).aggregate(avg=Avg('points_earned'))['avg'] or 0
            
            # Next assignment due
            next_assignment = Assignment.objects.filter(
                section=section,
                due_date__gte=timezone.now()
            ).order_by('due_date').first()
            
            my_sections_data.append({
                'id': section.id,
                'section_name': section.section_name,
                'subject_name': section.subject.subject_name,
                'student_count': student_count,
                'assignment_count': assignment_count,
                'pending_submissions': pending_submissions,
                'avg_grade': float(avg_grade) if avg_grade else 0,
                'next_assignment_due': next_assignment.due_date.isoformat() if next_assignment else None
            })
        
        # Recent submissions
        recent_submissions = []
        for submission in Submission.objects.filter(
            assignment__section__in=my_sections,
            status='SUBMITTED'
        ).select_related('student', 'assignment').order_by('-submitted_at')[:10]:
            recent_submissions.append({
                'id': submission.id,
                'student_name': f"{submission.student.first_name} {submission.student.last_name}",
                'assignment_title': submission.assignment.title,
                'section_name': submission.assignment.section.section_name,
                'submitted_at': submission.submitted_at.isoformat(),
                'is_late': submission.submitted_at > submission.assignment.due_date,
                'needs_grading': submission.status == 'SUBMITTED'
            })
        
        # Assignment performance
        assignment_performance = []
        for assignment in Assignment.objects.filter(section__in=my_sections).order_by('-due_date')[:10]:
            submissions = Submission.objects.filter(assignment=assignment)
            total_students = Enrollment.objects.filter(
                section=assignment.section,
                status='ENROLLED'
            ).count()
            
            avg_grade = submissions.filter(
                points_earned__isnull=False
            ).aggregate(avg=Avg('points_earned'))['avg'] or 0
            
            completion_rate = (submissions.count() / total_students * 100) if total_students > 0 else 0
            late_rate = (submissions.filter(
                submitted_at__gt=assignment.due_date
            ).count() / submissions.count() * 100) if submissions.count() > 0 else 0
            
            assignment_performance.append({
                'assignment_title': assignment.title,
                'avg_grade': float(avg_grade) if avg_grade else 0,
                'completion_rate': completion_rate,
                'late_rate': late_rate
            })
        
        # Upcoming deadlines
        upcoming_deadlines = []
        for assignment in Assignment.objects.filter(
            section__in=my_sections,
            due_date__gte=timezone.now()
        ).order_by('due_date')[:5]:
            submission_count = Submission.objects.filter(assignment=assignment).count()
            total_students = Enrollment.objects.filter(
                section=assignment.section,
                status='ENROLLED'
            ).count()
            
            upcoming_deadlines.append({
                'assignment_title': assignment.title,
                'section_name': assignment.section.section_name,
                'due_date': assignment.due_date.isoformat(),
                'submission_count': submission_count,
                'total_students': total_students
            })
        
        # Grade distribution
        grade_distribution = [
            {'range': 'A (90-100)', 'count': 0, 'percentage': 0},
            {'range': 'B (80-89)', 'count': 0, 'percentage': 0},
            {'range': 'C (70-79)', 'count': 0, 'percentage': 0},
            {'range': 'D (60-69)', 'count': 0, 'percentage': 0},
            {'range': 'F (0-59)', 'count': 0, 'percentage': 0}
        ]
        
        # Calculate actual grade distribution
        submissions_with_grades = Submission.objects.filter(
            assignment__section__in=my_sections,
            points_earned__isnull=False
        )
        
        total_graded = submissions_with_grades.count()
        if total_graded > 0:
            for submission in submissions_with_grades:
                percentage = (submission.points_earned / submission.assignment.total_points) * 100
                if percentage >= 90:
                    grade_distribution[0]['count'] += 1
                elif percentage >= 80:
                    grade_distribution[1]['count'] += 1
                elif percentage >= 70:
                    grade_distribution[2]['count'] += 1
                elif percentage >= 60:
                    grade_distribution[3]['count'] += 1
                else:
                    grade_distribution[4]['count'] += 1
            
            # Calculate percentages
            for grade in grade_distribution:
                grade['percentage'] = (grade['count'] / total_graded * 100) if total_graded > 0 else 0
        
        data = {
            'stats': {
                'my_sections': my_sections.count(),
                'total_students': total_students,
                'total_assignments': total_assignments,
                'pending_grading': pending_grading,
                'average_class_grade': float(avg_class_grade) if avg_class_grade else 0,
                'late_submissions': late_submissions
            },
            'my_sections': my_sections_data,
            'recent_submissions': recent_submissions,
            'assignment_performance': assignment_performance,
            'upcoming_deadlines': upcoming_deadlines,
            'grade_distribution': grade_distribution
        }
        
        serializer = ProfessorDashboardSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated & IsStudent])
    def student(self, request):
        """Student dashboard data"""
        student = request.user
        school = student.school
        
        # My enrollments
        my_enrollments = Enrollment.objects.filter(
            student=student,
            status='ENROLLED'
        ).select_related('section', 'section__subject', 'section__professor')
        
        # Basic stats
        enrolled_sections = my_enrollments.count()
        total_assignments = Assignment.objects.filter(
            section__in=[enrollment.section for enrollment in my_enrollments]
        ).count()
        
        # Calculate completed assignments
        completed_assignments = Submission.objects.filter(
            student=student,
            status__in=['GRADED', 'RETURNED']
        ).count()
        
        pending_assignments = Assignment.objects.filter(
            section__in=[enrollment.section for enrollment in my_enrollments],
            due_date__gte=timezone.now()
        ).exclude(
            submissions__student=student,
            submissions__status__in=['SUBMITTED', 'GRADED', 'RETURNED']
        ).count()
        
        # Calculate average grade
        avg_grade = Submission.objects.filter(
            student=student,
            points_earned__isnull=False
        ).aggregate(avg=Avg('points_earned'))['avg'] or 0
        
        # Calculate GPA (simplified)
        gpa = (avg_grade / 25) if avg_grade > 0 else 0  # Convert to 4.0 scale
        
        # Enrolled sections data
        enrolled_sections_data = []
        for enrollment in my_enrollments:
            section = enrollment.section
            assignment_count = Assignment.objects.filter(section=section).count()
            
            # Calculate current grade for this section
            section_submissions = Submission.objects.filter(
                student=student,
                assignment__section=section,
                points_earned__isnull=False
            )
            
            current_grade = section_submissions.aggregate(avg=Avg('points_earned'))['avg'] or 0
            
            # Next assignment due
            next_assignment = Assignment.objects.filter(
                section=section,
                due_date__gte=timezone.now()
            ).exclude(
                submissions__student=student,
                submissions__status__in=['SUBMITTED', 'GRADED', 'RETURNED']
            ).order_by('due_date').first()
            
            enrolled_sections_data.append({
                'id': section.id,
                'section_name': section.section_name,
                'subject_name': section.subject.subject_name,
                'subject_code': section.subject.subject_code,
                'professor_name': f"{section.professor.first_name} {section.professor.last_name}" if section.professor else 'No Professor',
                'current_grade': float(current_grade) if current_grade else 0,
                'assignment_count': assignment_count,
                'next_assignment_due': next_assignment.due_date.isoformat() if next_assignment else None
            })
        
        # Recent assignments
        recent_assignments = []
        for assignment in Assignment.objects.filter(
            section__in=[enrollment.section for enrollment in my_enrollments]
        ).order_by('-due_date')[:10]:
            submission = Submission.objects.filter(
                student=student,
                assignment=assignment
            ).first()
            
            status = 'pending'
            grade = None
            is_late = False
            
            if submission:
                if submission.status == 'SUBMITTED':
                    status = 'submitted'
                elif submission.status in ['GRADED', 'RETURNED']:
                    status = 'graded'
                    grade = submission.points_earned
                is_late = submission.submitted_at and submission.submitted_at > assignment.due_date
            elif assignment.due_date < timezone.now():
                status = 'overdue'
            
            recent_assignments.append({
                'id': assignment.id,
                'title': assignment.title,
                'subject_name': assignment.section.subject.subject_name,
                'due_date': assignment.due_date.isoformat(),
                'status': status,
                'grade': float(grade) if grade else None,
                'max_points': float(assignment.total_points),
                'is_late': is_late
            })
        
        # Upcoming deadlines
        upcoming_deadlines = []
        for assignment in Assignment.objects.filter(
            section__in=[enrollment.section for enrollment in my_enrollments],
            due_date__gte=timezone.now()
        ).exclude(
            submissions__student=student,
            submissions__status__in=['SUBMITTED', 'GRADED', 'RETURNED']
        ).order_by('due_date')[:5]:
            hours_remaining = int((assignment.due_date - timezone.now()).total_seconds() / 3600)
            
            upcoming_deadlines.append({
                'id': assignment.id,
                'title': assignment.title,
                'section_name': assignment.section.section_name,
                'due_date': assignment.due_date.isoformat(),
                'max_points': float(assignment.total_points),
                'hours_remaining': max(0, hours_remaining)
            })
        
        # Grade trends
        grade_trends = []
        for submission in Submission.objects.filter(
            student=student,
            points_earned__isnull=False
        ).select_related('assignment').order_by('-submitted_at')[:10]:
            grade_trends.append({
                'assignment_title': submission.assignment.title,
                'grade': float(submission.points_earned),
                'max_points': float(submission.assignment.total_points),
                'submitted_at': submission.submitted_at.isoformat()
            })
        
        # Performance by subject
        performance_by_subject = []
        for enrollment in my_enrollments:
            subject = enrollment.section.subject
            
            # Get all submissions for this subject
            subject_submissions = Submission.objects.filter(
                student=student,
                assignment__section__subject=subject,
                points_earned__isnull=False
            )
            
            if subject_submissions.exists():
                avg_grade = subject_submissions.aggregate(avg=Avg('points_earned'))['avg'] or 0
                assignment_count = Assignment.objects.filter(
                    section__subject=subject,
                    section__in=[enrollment.section for enrollment in my_enrollments]
                ).count()
                completion_rate = (subject_submissions.count() / assignment_count * 100) if assignment_count > 0 else 0
                
                performance_by_subject.append({
                    'subject_name': subject.subject_name,
                    'avg_grade': float(avg_grade) if avg_grade else 0,
                    'assignment_count': assignment_count,
                    'completion_rate': completion_rate
                })
        
        data = {
            'stats': {
                'enrolled_sections': enrolled_sections,
                'total_assignments': total_assignments,
                'completed_assignments': completed_assignments,
                'pending_assignments': pending_assignments,
                'average_grade': float(avg_grade) if avg_grade else 0,
                'gpa': gpa
            },
            'enrolled_sections': enrolled_sections_data,
            'recent_assignments': recent_assignments,
            'upcoming_deadlines': upcoming_deadlines,
            'grade_trends': grade_trends,
            'performance_by_subject': performance_by_subject
        }
        
        serializer = StudentDashboardSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def system_health(self, request):
        """Real-time system health metrics for all authenticated users"""
        start_time = time.time()
        
        # Get comprehensive health metrics
        health_metrics = SystemMonitor.get_cached_health()
        
        # Add current request response time
        health_metrics['current_request_time'] = round((time.time() - start_time) * 1000, 2)
        
        return Response(health_metrics)

    @action(detail=False, methods=['get'])
    def quick_stats(self, request):
        """Quick stats for any authenticated user"""
        user = request.user
        
        # Basic stats that apply to all users
        notifications = random.randint(1, 10)  # Mock notifications
        pending_tasks = 0
        recent_activity = "Active"
        
        # Role-specific pending tasks
        if user.role == 'PROFESSOR':
            pending_tasks = Submission.objects.filter(
                assignment__section__professor=user,
                status='SUBMITTED'
            ).count()
        elif user.role == 'STUDENT':
            pending_tasks = Assignment.objects.filter(
                section__enrollments__student=user,
                due_date__gte=timezone.now()
            ).exclude(
                submissions__student=user,
                submissions__status__in=['SUBMITTED', 'GRADED', 'RETURNED']
            ).count()
        elif user.role == 'ADMIN':
            pending_tasks = Submission.objects.filter(
                school=user.school,
                status='SUBMITTED'
            ).count()
        
        data = {
            'notifications': notifications,
            'pending_tasks': pending_tasks,
            'recent_activity': recent_activity
        }
        
        serializer = QuickStatsSerializer(data)
        return Response(serializer.data)