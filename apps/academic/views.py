from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from .models import Subject, Section, Enrollment, Assignment, Submission
from .serializers import (
    SubjectSerializer, SectionSerializer, EnrollmentSerializer,
    AssignmentSerializer, SubmissionSerializer, StudentEnrollmentSerializer,
    GradeSubmissionSerializer
)
from apps.base import TenantAwareViewSet
from apps.permissions import IsSchoolAdmin, IsProfessor, IsStudent, IsSameSchool
from apps.users.models import User

class SubjectViewSet(TenantAwareViewSet):
    """
    ViewSet for managing subjects within a school.
    """
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSchoolAdmin]
        else:
            permission_classes = [IsAuthenticated, IsSameSchool]
        return [permission() for permission in permission_classes]

class SectionViewSet(TenantAwareViewSet):
    """
    ViewSet for managing sections within a school.
    """
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSchoolAdmin]
        else:
            permission_classes = [IsAuthenticated, IsSameSchool]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.role == User.Role.PROFESSOR:
            queryset = queryset.filter(professor=user)
        elif user.role == User.Role.STUDENT:
            enrolled_sections = user.enrollments.filter(
                status=Enrollment.StatusChoices.ENROLLED
            ).values_list('section', flat=True)
            queryset = queryset.filter(id__in=enrolled_sections)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get all students enrolled in a section"""
        section = self.get_object()
        enrollments = section.enrollments.filter(status=Enrollment.StatusChoices.ENROLLED)
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

class EnrollmentViewSet(TenantAwareViewSet):
    """
    ViewSet for managing enrollments within a school.
    """
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsSchoolAdmin | IsStudent]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsSchoolAdmin | IsProfessor]
        elif self.action == 'destroy':
            permission_classes = [IsSchoolAdmin]
        else:
            permission_classes = [IsAuthenticated, IsSameSchool]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.role == User.Role.STUDENT:
            queryset = queryset.filter(student=user)
        elif user.role == User.Role.PROFESSOR:
            queryset = queryset.filter(section__professor=user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Handle enrollment creation"""
        user = self.request.user
        if user.role == User.Role.STUDENT:
            serializer.save(school=user.school, student=user)
        else:
            super().perform_create(serializer)
    
    @action(detail=False, methods=['get'])
    def my_enrollments(self, request):
        """Get current student's enrollments"""
        if request.user.role != User.Role.STUDENT:
            return Response(
                {'error': 'This endpoint is only for students'},
                status=status.HTTP_403_FORBIDDEN
            )
        enrollments = request.user.enrollments.all()
        serializer = StudentEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

class AssignmentViewSet(TenantAwareViewSet):
    """
    ViewSet for managing assignments within a school.
    """
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsProfessor | IsSchoolAdmin]
        else:
            permission_classes = [IsAuthenticated, IsSameSchool]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.role == User.Role.PROFESSOR:
            queryset = queryset.filter(section__professor=user)
        elif user.role == User.Role.STUDENT:
            enrolled_sections = user.enrollments.filter(
                status=Enrollment.StatusChoices.ENROLLED
            ).values_list('section', flat=True)
            queryset = queryset.filter(section__in=enrolled_sections)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the created_by field"""
        serializer.save(school=self.request.user.school, created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """Get all submissions for an assignment"""
        assignment = self.get_object()
        user = request.user
        
        if user.role == User.Role.STUDENT:
            submissions = assignment.submissions.filter(student=user)
        else:
            submissions = assignment.submissions.all()
        
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

class SubmissionViewSet(TenantAwareViewSet):
    """
    ViewSet for managing submissions within a school.
    """
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    
    def get_permissions(self):
        if self.action == 'grade':
            permission_classes = [IsProfessor | IsSchoolAdmin]
        else:
            permission_classes = [IsAuthenticated, IsSameSchool]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.role == User.Role.STUDENT:
            queryset = queryset.filter(student=user)
        elif user.role == User.Role.PROFESSOR:
            queryset = queryset.filter(assignment__section__professor=user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Handle submission creation"""
        user = self.request.user
        if user.role == User.Role.STUDENT:
            serializer.save(school=user.school, student=user)
        else:
            super().perform_create(serializer)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit an assignment"""
        submission = self.get_object()
        if submission.student != request.user:
            return Response(
                {'error': 'You can only submit your own assignments'},
                status=status.HTTP_403_FORBIDDEN
            )
        submission.status = Submission.StatusChoices.SUBMITTED
        submission.submitted_at = timezone.now()
        submission.save()
        return Response({'status': 'Assignment submitted successfully'})
    
    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        """Grade a submission"""
        submission = self.get_object()
        serializer = GradeSubmissionSerializer(data=request.data)
        
        if serializer.is_valid():
            submission.points_earned = serializer.validated_data['points_earned']
            submission.feedback = serializer.validated_data.get('feedback', '')
            submission.status = Submission.StatusChoices.GRADED
            submission.graded_by = request.user
            submission.graded_at = timezone.now()
            submission.save()
            
            return Response(SubmissionSerializer(submission).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)