from rest_framework import serializers
from .models import Subject, Section, Enrollment, Assignment, Submission
from apps.users.serializers import UserSerializer

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'subject_name', 'subject_code', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class SectionSerializer(serializers.ModelSerializer):
    subject_info = SubjectSerializer(source='subject', read_only=True)
    professor_info = UserSerializer(source='professor', read_only=True)
    enrollment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Section
        fields = ['id', 'section_name', 'subject', 'subject_info', 'professor', 'professor_info', 
                 'start_date', 'end_date', 'max_students', 'enrollment_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_enrollment_count(self, obj):
        return obj.enrollments.filter(status=Enrollment.StatusChoices.ENROLLED).count()

class EnrollmentSerializer(serializers.ModelSerializer):
    student_info = UserSerializer(source='student', read_only=True)
    section_info = SectionSerializer(source='section', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_info', 'section', 'section_info', 'status', 
                 'enrollment_date', 'grade']
        read_only_fields = ['enrollment_date']

class AssignmentSerializer(serializers.ModelSerializer):
    section_info = SectionSerializer(source='section', read_only=True)
    created_by_info = UserSerializer(source='created_by', read_only=True)
    
    class Meta:
        model = Assignment
        fields = ['id', 'section', 'section_info', 'title', 'description', 'due_date', 
                 'total_points', 'created_by', 'created_by_info', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'created_by']

class SubmissionSerializer(serializers.ModelSerializer):
    assignment_info = AssignmentSerializer(source='assignment', read_only=True)
    student_info = UserSerializer(source='student', read_only=True)
    graded_by_info = UserSerializer(source='graded_by', read_only=True)
    
    class Meta:
        model = Submission
        fields = ['id', 'assignment', 'assignment_info', 'student', 'student_info', 'status', 
                 'content', 'file_url', 'submitted_at', 'points_earned', 'feedback', 
                 'graded_by', 'graded_by_info', 'graded_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'submitted_at', 'graded_at', 'graded_by']

class StudentEnrollmentSerializer(serializers.ModelSerializer):
    """Simplified serializer for students viewing their enrollments"""
    section_name = serializers.CharField(source='section.section_name', read_only=True)
    subject_name = serializers.CharField(source='section.subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='section.subject.subject_code', read_only=True)
    professor_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = ['id', 'section_name', 'subject_name', 'subject_code', 'professor_name', 
                 'status', 'enrollment_date', 'grade']
    
    def get_professor_name(self, obj):
        if obj.section.professor:
            return f"{obj.section.professor.first_name} {obj.section.professor.last_name}"
        return None

class GradeSubmissionSerializer(serializers.Serializer):
    points_earned = serializers.DecimalField(max_digits=5, decimal_places=2)
    feedback = serializers.CharField(allow_blank=True, required=False)