from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import datetime, timedelta

from apps.users.models import User
from apps.academic.models import Section, Assignment, Submission, Enrollment
from apps.organizations.models import School
from .serializers import (
    UserReportSerializer, SectionReportSerializer, AssignmentReportSerializer,
    SubmissionReportSerializer, EnrollmentReportSerializer
)


class UserReportView(generics.ListAPIView):
    """
    API view to retrieve user reports with filtering capabilities
    """
    serializer_class = UserReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(date_joined__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(date_joined__lte=end_date)
            except ValueError:
                pass
        
        # Filter by school
        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        
        return queryset.select_related('school').order_by('-date_joined')


class SectionReportView(generics.ListAPIView):
    """
    API view to retrieve section reports with filtering capabilities
    """
    serializer_class = SectionReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Section.objects.all()
        
        # Filter by subject
        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        # Filter by professor
        professor_id = self.request.query_params.get('professor_id')
        if professor_id:
            queryset = queryset.filter(professor_id=professor_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__lte=end_date)
            except ValueError:
                pass
        
        return queryset.select_related('subject', 'professor').order_by('-created_at')


class AssignmentReportView(generics.ListAPIView):
    """
    API view to retrieve assignment reports with filtering capabilities
    """
    serializer_class = AssignmentReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Assignment.objects.all()
        
        # Filter by section
        section_id = self.request.query_params.get('section_id')
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        
        # Filter by section
        section_id = self.request.query_params.get('section_id')
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__lte=end_date)
            except ValueError:
                pass
        
        return queryset.select_related('section__subject', 'section__professor').order_by('-created_at')


class SubmissionReportView(generics.ListAPIView):
    """
    API view to retrieve submission/grade reports with filtering capabilities
    """
    serializer_class = SubmissionReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Submission.objects.filter(status='GRADED')
        
        # Filter by student
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Filter by section
        section_id = self.request.query_params.get('section_id')
        if section_id:
            queryset = queryset.filter(assignment__section_id=section_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(graded_at__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(graded_at__lte=end_date)
            except ValueError:
                pass
        
        return queryset.select_related(
            'student', 'assignment__section__subject', 'assignment__section__professor'
        ).order_by('-graded_at')


class EnrollmentReportView(generics.ListAPIView):
    """
    API view to retrieve enrollment reports with filtering capabilities
    """
    serializer_class = EnrollmentReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Enrollment.objects.all()
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by student
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Filter by section
        section_id = self.request.query_params.get('section_id')
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(enrollment_date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(enrollment_date__lte=end_date)
            except ValueError:
                pass
        
        return queryset.select_related(
            'student', 'section__subject', 'section__professor'
        ).order_by('-enrollment_date')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_report_view(request):
    """
    API view to retrieve system-wide analytics (SuperAdmin only)
    """
    user = request.user
    if user.role != 'SUPERADMIN':
        return Response(
            {'error': 'Permission denied. SuperAdmin access required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Calculate system statistics
    total_schools = School.objects.count()
    total_users = User.objects.count()
    total_sections = Section.objects.count()
    total_assignments = Assignment.objects.count()
    total_submissions = Submission.objects.filter(status__in=['SUBMITTED', 'GRADED']).count()
    total_grades = Submission.objects.filter(status='GRADED').count()
    
    # User growth over last 12 months
    now = timezone.now()
    user_growth = []
    for i in range(12):
        month_start = now - timedelta(days=30 * (i + 1))
        month_end = now - timedelta(days=30 * i)
        new_users = User.objects.filter(
            date_joined__gte=month_start,
            date_joined__lt=month_end
        ).count()
        user_growth.append({
            'date': month_start.strftime('%Y-%m'),
            'new_users': new_users
        })
    
    # Grade distribution based on percentage
    grade_distribution = []
    graded_submissions = Submission.objects.filter(
        status='GRADED',
        points_earned__isnull=False,
        assignment__total_points__gt=0
    )
    total_grades_count = graded_submissions.count()
    
    if total_grades_count > 0:
        for grade_letter in ['A', 'B', 'C', 'D', 'F']:
            count = 0
            for submission in graded_submissions:
                percentage = (float(submission.points_earned) / float(submission.assignment.total_points)) * 100
                if grade_letter == 'A' and percentage >= 90:
                    count += 1
                elif grade_letter == 'B' and 80 <= percentage < 90:
                    count += 1
                elif grade_letter == 'C' and 70 <= percentage < 80:
                    count += 1
                elif grade_letter == 'D' and 60 <= percentage < 70:
                    count += 1
                elif grade_letter == 'F' and percentage < 60:
                    count += 1
            
            grade_distribution.append({
                'grade': grade_letter,
                'count': count,
                'percentage': round((count / total_grades_count) * 100, 2) if total_grades_count > 0 else 0
            })
    
    # Assignment distribution by section
    assignment_distribution = list(
        Assignment.objects.values('section__subject__subject_name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # Monthly activity for last 6 months
    monthly_activity = []
    for i in range(6):
        month_start = now - timedelta(days=30 * (i + 1))
        month_end = now - timedelta(days=30 * i)
        
        new_users = User.objects.filter(
            date_joined__gte=month_start,
            date_joined__lt=month_end
        ).count()
        
        new_assignments = Assignment.objects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        
        new_submissions = Submission.objects.filter(
            graded_at__gte=month_start,
            graded_at__lt=month_end,
            status='GRADED'
        ).count()
        
        monthly_activity.append({
            'month': month_start.strftime('%Y-%m'),
            'new_users': new_users,
            'new_assignments': new_assignments,
            'new_submissions': new_submissions
        })
    
    system_data = {
        'total_schools': total_schools,
        'total_users': total_users,
        'total_sections': total_sections,
        'total_assignments': total_assignments,
        'total_submissions': total_submissions,
        'total_grades': total_grades,
        'user_growth': user_growth,
        'grade_distribution': grade_distribution,
        'assignment_distribution': assignment_distribution,
        'monthly_activity': monthly_activity
    }
    
    return Response(system_data)