from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum, F
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
import csv
import io

from apps.users.models import User
from apps.organizations.models import School
from apps.academic.models import Subject, Section, Assignment, Submission, Enrollment
from apps.permissions import IsSuperAdmin, IsSchoolAdmin, IsProfessor, IsStudent
from .serializers import (
    UserReportSerializer,
    SectionReportSerializer,
    AssignmentReportSerializer,
    GradeReportSerializer,
    EnrollmentReportSerializer,
    SystemReportSerializer
)


class ReportsViewSet(ViewSet):
    """Reports endpoints for different user roles"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def users(self, request):
        """User reports - accessible by Admin and SuperAdmin"""
        user = request.user
        
        if user.role == 'SUPERADMIN':
            # SuperAdmin can see all users
            users = User.objects.exclude(role='SUPERADMIN')
        elif user.role == 'ADMIN':
            # Admin can only see users in their school
            users = User.objects.filter(school=user.school).exclude(role='SUPERADMIN')
        else:
            return Response(
                {'error': 'Permission denied. Only admins can access user reports.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Apply filters
        role_filter = request.query_params.get('role', None)
        if role_filter:
            users = users.filter(role=role_filter)
        
        is_active_filter = request.query_params.get('is_active', None)
        if is_active_filter is not None:
            users = users.filter(is_active=is_active_filter.lower() == 'true')
        
        # Ordering
        ordering = request.query_params.get('ordering', '-date_joined')
        users = users.order_by(ordering)
        
        serializer = UserReportSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def sections(self, request):
        """Section reports - accessible by Admin, Professor, and SuperAdmin"""
        user = request.user
        
        if user.role == 'SUPERADMIN':
            sections = Section.objects.all()
        elif user.role == 'ADMIN':
            sections = Section.objects.filter(school=user.school)
        elif user.role == 'PROFESSOR':
            sections = Section.objects.filter(school=user.school, professor=user)
        else:
            return Response(
                {'error': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Apply filters
        subject_filter = request.query_params.get('subject', None)
        if subject_filter:
            sections = sections.filter(subject_id=subject_filter)
        
        professor_filter = request.query_params.get('professor', None)
        if professor_filter:
            sections = sections.filter(professor_id=professor_filter)
        
        # Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        sections = sections.order_by(ordering)
        
        serializer = SectionReportSerializer(sections, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def assignments(self, request):
        """Assignment reports - accessible by Admin, Professor, and SuperAdmin"""
        user = request.user
        
        if user.role == 'SUPERADMIN':
            assignments = Assignment.objects.all()
        elif user.role == 'ADMIN':
            assignments = Assignment.objects.filter(school=user.school)
        elif user.role == 'PROFESSOR':
            assignments = Assignment.objects.filter(section__school=user.school, section__professor=user)
        else:
            return Response(
                {'error': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Apply filters
        section_filter = request.query_params.get('section', None)
        if section_filter:
            assignments = assignments.filter(section_id=section_filter)
        
        assignment_type_filter = request.query_params.get('assignment_type', None)
        if assignment_type_filter:
            assignments = assignments.filter(title__icontains=assignment_type_filter.lower())
        
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        
        if date_from:
            assignments = assignments.filter(due_date__gte=date_from)
        if date_to:
            assignments = assignments.filter(due_date__lte=date_to)
        
        # Ordering
        ordering = request.query_params.get('ordering', '-due_date')
        assignments = assignments.order_by(ordering)
        
        serializer = AssignmentReportSerializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def grades(self, request):
        """Grade reports - accessible by Admin, Professor, and SuperAdmin"""
        user = request.user
        
        if user.role == 'SUPERADMIN':
            submissions = Submission.objects.filter(points_earned__isnull=False)
        elif user.role == 'ADMIN':
            submissions = Submission.objects.filter(
                school=user.school,
                points_earned__isnull=False
            )
        elif user.role == 'PROFESSOR':
            submissions = Submission.objects.filter(
                assignment__section__school=user.school,
                assignment__section__professor=user,
                points_earned__isnull=False
            )
        elif user.role == 'STUDENT':
            # Students can only see their own grades
            submissions = Submission.objects.filter(
                student=user,
                points_earned__isnull=False
            )
        else:
            return Response(
                {'error': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Apply filters
        student_filter = request.query_params.get('student', None)
        if student_filter and user.role != 'STUDENT':
            submissions = submissions.filter(student_id=student_filter)
        
        section_filter = request.query_params.get('section', None)
        if section_filter:
            submissions = submissions.filter(assignment__section_id=section_filter)
        
        assignment_filter = request.query_params.get('assignment', None)
        if assignment_filter:
            submissions = submissions.filter(assignment_id=assignment_filter)
        
        grade_min = request.query_params.get('grade_min', None)
        grade_max = request.query_params.get('grade_max', None)
        
        if grade_min:
            submissions = submissions.filter(points_earned__gte=grade_min)
        if grade_max:
            submissions = submissions.filter(points_earned__lte=grade_max)
        
        # Ordering
        ordering = request.query_params.get('ordering', '-graded_at')
        submissions = submissions.order_by(ordering)
        
        serializer = GradeReportSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def enrollments(self, request):
        """Enrollment reports - accessible by Admin, Professor, and SuperAdmin"""
        user = request.user
        
        if user.role == 'SUPERADMIN':
            enrollments = Enrollment.objects.all()
        elif user.role == 'ADMIN':
            enrollments = Enrollment.objects.filter(section__school=user.school)
        elif user.role == 'PROFESSOR':
            enrollments = Enrollment.objects.filter(
                section__school=user.school,
                section__professor=user
            )
        else:
            return Response(
                {'error': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Apply filters
        student_filter = request.query_params.get('student', None)
        if student_filter:
            enrollments = enrollments.filter(student_id=student_filter)
        
        section_filter = request.query_params.get('section', None)
        if section_filter:
            enrollments = enrollments.filter(section_id=section_filter)
        
        status_filter = request.query_params.get('status', None)
        if status_filter:
            enrollments = enrollments.filter(status=status_filter)
        
        # Ordering
        ordering = request.query_params.get('ordering', '-enrollment_date')
        enrollments = enrollments.order_by(ordering)
        
        serializer = EnrollmentReportSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated & IsSuperAdmin])
    def system(self, request):
        """System-wide reports - accessible only by SuperAdmin"""
        now = timezone.now()
        
        # Basic counts
        total_schools = School.objects.count()
        total_users = User.objects.exclude(role='SUPERADMIN').count()
        total_sections = Section.objects.count()
        total_assignments = Assignment.objects.count()
        total_submissions = Submission.objects.count()
        total_grades = Submission.objects.filter(points_earned__isnull=False).count()
        
        # User growth (last 30 days)
        user_growth = []
        for i in range(30):
            date = now - timedelta(days=i)
            new_users = User.objects.filter(
                date_joined__date=date.date()
            ).exclude(role='SUPERADMIN').count()
            user_growth.append({
                'date': date.date().isoformat(),
                'new_users': new_users
            })
        user_growth.reverse()
        
        # Grade distribution
        grade_ranges = [
            ('A', 90, 100),
            ('B', 80, 89),
            ('C', 70, 79),
            ('D', 60, 69),
            ('F', 0, 59)
        ]
        
        grade_distribution = []
        total_graded = Submission.objects.filter(points_earned__isnull=False).count()
        
        for grade_letter, min_percent, max_percent in grade_ranges:
            count = 0
            for submission in Submission.objects.filter(points_earned__isnull=False):
                percentage = (submission.points_earned / submission.assignment.total_points) * 100
                if min_percent <= percentage <= max_percent:
                    count += 1
            
            grade_distribution.append({
                'grade': grade_letter,
                'count': count,
                'percentage': (count / total_graded * 100) if total_graded > 0 else 0
            })
        
        # Assignment type distribution
        assignment_types = ['HOMEWORK', 'QUIZ', 'EXAM', 'PROJECT', 'DISCUSSION']
        assignment_type_distribution = []
        
        for assignment_type in assignment_types:
            count = Assignment.objects.filter(title__icontains=assignment_type.lower()).count()
            assignment_type_distribution.append({
                'type': assignment_type,
                'count': count
            })
        
        # Monthly activity (last 12 months)
        monthly_activity = []
        for i in range(12):
            month_start = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            new_users = User.objects.filter(
                date_joined__range=[month_start, month_end]
            ).exclude(role='SUPERADMIN').count()
            
            new_assignments = Assignment.objects.filter(
                created_at__range=[month_start, month_end]
            ).count()
            
            new_submissions = Submission.objects.filter(
                submitted_at__range=[month_start, month_end]
            ).count()
            
            monthly_activity.append({
                'month': month_start.strftime('%Y-%m'),
                'new_users': new_users,
                'new_assignments': new_assignments,
                'new_submissions': new_submissions
            })
        monthly_activity.reverse()
        
        data = {
            'total_schools': total_schools,
            'total_users': total_users,
            'total_sections': total_sections,
            'total_assignments': total_assignments,
            'total_submissions': total_submissions,
            'total_grades': total_grades,
            'user_growth': user_growth,
            'grade_distribution': grade_distribution,
            'assignment_type_distribution': assignment_type_distribution,
            'monthly_activity': monthly_activity
        }
        
        serializer = SystemReportSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def export_csv(self, request):
        """Export reports to CSV format"""
        report_type = request.query_params.get('type', 'users')
        user = request.user
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'users':
            if user.role not in ['ADMIN', 'SUPERADMIN']:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
            writer.writerow(['ID', 'Username', 'First Name', 'Last Name', 'Email', 'Role', 'School', 'Active', 'Date Joined'])
            
            if user.role == 'SUPERADMIN':
                users = User.objects.exclude(role='SUPERADMIN')
            else:
                users = User.objects.filter(school=user.school).exclude(role='SUPERADMIN')
            
            for user_obj in users:
                writer.writerow([
                    user_obj.id,
                    user_obj.username,
                    user_obj.first_name,
                    user_obj.last_name,
                    user_obj.email,
                    user_obj.role,
                    user_obj.school.name if user_obj.school else 'N/A',
                    user_obj.is_active,
                    user_obj.date_joined.strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        elif report_type == 'grades':
            writer.writerow(['ID', 'Student', 'Assignment', 'Section', 'Points Earned', 'Max Points', 'Percentage', 'Grade', 'Submitted At', 'Graded At'])
            
            if user.role == 'SUPERADMIN':
                submissions = Submission.objects.filter(points_earned__isnull=False)
            elif user.role == 'ADMIN':
                submissions = Submission.objects.filter(school=user.school, points_earned__isnull=False)
            elif user.role == 'PROFESSOR':
                submissions = Submission.objects.filter(
                    assignment__section__school=user.school,
                    assignment__section__professor=user,
                    points_earned__isnull=False
                )
            elif user.role == 'STUDENT':
                submissions = Submission.objects.filter(student=user, points_earned__isnull=False)
            else:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
            for submission in submissions:
                percentage = (submission.points_earned / submission.assignment.total_points) * 100
                grade_letter = 'A' if percentage >= 90 else 'B' if percentage >= 80 else 'C' if percentage >= 70 else 'D' if percentage >= 60 else 'F'
                
                writer.writerow([
                    submission.id,
                    f"{submission.student.first_name} {submission.student.last_name}",
                    submission.assignment.title,
                    submission.assignment.section.section_name,
                    submission.points_earned,
                    submission.assignment.total_points,
                    f"{percentage:.2f}%",
                    grade_letter,
                    submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submission.submitted_at else 'N/A',
                    submission.graded_at.strftime('%Y-%m-%d %H:%M:%S') if submission.graded_at else 'N/A'
                ])
        
        else:
            return Response({'error': 'Invalid report type'}, status=status.HTTP_400_BAD_REQUEST)
        
        return response

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def analytics(self, request):
        """Analytics data for charts and visualizations"""
        user = request.user
        
        if user.role == 'SUPERADMIN':
            # System-wide analytics
            analytics_data = {
                'school_growth': self._get_school_growth(),
                'user_distribution': self._get_user_distribution(),
                'assignment_trends': self._get_assignment_trends(),
                'grade_analytics': self._get_grade_analytics()
            }
        elif user.role == 'ADMIN':
            # School-specific analytics
            analytics_data = {
                'user_distribution': self._get_user_distribution(user.school),
                'section_performance': self._get_section_performance(user.school),
                'assignment_trends': self._get_assignment_trends(user.school),
                'grade_analytics': self._get_grade_analytics(user.school)
            }
        elif user.role == 'PROFESSOR':
            # Professor-specific analytics
            analytics_data = {
                'class_performance': self._get_class_performance(user),
                'assignment_completion': self._get_assignment_completion(user),
                'grade_distribution': self._get_grade_distribution(user)
            }
        elif user.role == 'STUDENT':
            # Student-specific analytics
            analytics_data = {
                'personal_progress': self._get_personal_progress(user),
                'subject_performance': self._get_subject_performance(user),
                'grade_trends': self._get_grade_trends(user)
            }
        else:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response(analytics_data)

    # Helper methods for analytics
    def _get_school_growth(self):
        """Get school growth over time (SuperAdmin only)"""
        growth_data = []
        now = timezone.now()
        
        for i in range(12):
            month_start = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            new_schools = School.objects.filter(
                created_at__range=[month_start, month_end]
            ).count()
            
            growth_data.append({
                'month': month_start.strftime('%Y-%m'),
                'new_schools': new_schools
            })
        
        return list(reversed(growth_data))

    def _get_user_distribution(self, school=None):
        """Get user distribution by role"""
        query = User.objects.exclude(role='SUPERADMIN')
        if school:
            query = query.filter(school=school)
        
        distribution = query.values('role').annotate(count=Count('id'))
        return [{'role': item['role'], 'count': item['count']} for item in distribution]

    def _get_assignment_trends(self, school=None):
        """Get assignment creation trends"""
        query = Assignment.objects.all()
        if school:
            query = query.filter(school=school)
        
        trends = []
        now = timezone.now()
        
        for i in range(12):
            month_start = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            count = query.filter(created_at__range=[month_start, month_end]).count()
            trends.append({
                'month': month_start.strftime('%Y-%m'),
                'assignments': count
            })
        
        return list(reversed(trends))

    def _get_grade_analytics(self, school=None):
        """Get grade analytics"""
        query = Submission.objects.filter(points_earned__isnull=False)
        if school:
            query = query.filter(school=school)
        
        # Calculate average grade
        avg_grade = query.aggregate(avg=Avg('points_earned'))['avg'] or 0
        
        # Grade distribution
        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        
        for submission in query:
            percentage = (submission.points_earned / submission.assignment.total_points) * 100
            if percentage >= 90:
                distribution['A'] += 1
            elif percentage >= 80:
                distribution['B'] += 1
            elif percentage >= 70:
                distribution['C'] += 1
            elif percentage >= 60:
                distribution['D'] += 1
            else:
                distribution['F'] += 1
        
        return {
            'average_grade': avg_grade,
            'distribution': [{'grade': k, 'count': v} for k, v in distribution.items()]
        }

    def _get_section_performance(self, school):
        """Get section performance for a school"""
        sections = Section.objects.filter(school=school)
        performance = []
        
        for section in sections:
            avg_grade = Submission.objects.filter(
                assignment__section=section,
                points_earned__isnull=False
            ).aggregate(avg=Avg('points_earned'))['avg'] or 0
            
            performance.append({
                'section': section.section_name,
                'subject': section.subject.subject_name,
                'average_grade': avg_grade
            })
        
        return performance

    def _get_class_performance(self, professor):
        """Get class performance for a professor"""
        sections = Section.objects.filter(professor=professor)
        performance = []
        
        for section in sections:
            assignments_count = Assignment.objects.filter(section=section).count()
            submissions_count = Submission.objects.filter(assignment__section=section).count()
            avg_grade = Submission.objects.filter(
                assignment__section=section,
                points_earned__isnull=False
            ).aggregate(avg=Avg('points_earned'))['avg'] or 0
            
            performance.append({
                'section': section.section_name,
                'assignments': assignments_count,
                'submissions': submissions_count,
                'average_grade': avg_grade
            })
        
        return performance

    def _get_assignment_completion(self, professor):
        """Get assignment completion rates for a professor"""
        assignments = Assignment.objects.filter(section__professor=professor)
        completion_data = []
        
        for assignment in assignments:
            total_students = Enrollment.objects.filter(
                section=assignment.section,
                status='ENROLLED'
            ).count()
            submitted = Submission.objects.filter(assignment=assignment).count()
            completion_rate = (submitted / total_students * 100) if total_students > 0 else 0
            
            completion_data.append({
                'assignment': assignment.title,
                'completion_rate': completion_rate
            })
        
        return completion_data

    def _get_grade_distribution(self, professor):
        """Get grade distribution for a professor's classes"""
        submissions = Submission.objects.filter(
            assignment__section__professor=professor,
            points_earned__isnull=False
        )
        
        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        
        for submission in submissions:
            percentage = (submission.points_earned / submission.assignment.total_points) * 100
            if percentage >= 90:
                distribution['A'] += 1
            elif percentage >= 80:
                distribution['B'] += 1
            elif percentage >= 70:
                distribution['C'] += 1
            elif percentage >= 60:
                distribution['D'] += 1
            else:
                distribution['F'] += 1
        
        return [{'grade': k, 'count': v} for k, v in distribution.items()]

    def _get_personal_progress(self, student):
        """Get personal progress for a student"""
        submissions = Submission.objects.filter(
            student=student,
            points_earned__isnull=False
        ).order_by('submitted_at')
        
        progress = []
        for submission in submissions:
            percentage = (submission.points_earned / submission.assignment.total_points) * 100
            progress.append({
                'assignment': submission.assignment.title,
                'date': submission.submitted_at.strftime('%Y-%m-%d'),
                'grade': percentage
            })
        
        return progress

    def _get_subject_performance(self, student):
        """Get subject performance for a student"""
        enrollments = Enrollment.objects.filter(student=student, status='ENROLLED')
        performance = []
        
        for enrollment in enrollments:
            submissions = Submission.objects.filter(
                student=student,
                assignment__section=enrollment.section,
                points_earned__isnull=False
            )
            
            if submissions.exists():
                avg_grade = submissions.aggregate(avg=Avg('points_earned'))['avg']
                performance.append({
                    'subject': enrollment.section.subject.subject_name,
                    'section': enrollment.section.section_name,
                    'average_grade': avg_grade
                })
        
        return performance

    def _get_grade_trends(self, student):
        """Get grade trends over time for a student"""
        submissions = Submission.objects.filter(
            student=student,
            points_earned__isnull=False
        ).order_by('submitted_at')
        
        trends = []
        for submission in submissions[-10:]:  # Last 10 submissions
            percentage = (submission.points_earned / submission.assignment.total_points) * 100
            trends.append({
                'date': submission.submitted_at.strftime('%Y-%m-%d'),
                'grade': percentage
            })
        
        return trends