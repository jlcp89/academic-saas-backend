from rest_framework import serializers
from apps.users.models import User
from apps.organizations.models import School
from apps.academic.models import Section, Assignment, Submission, Enrollment


class UserReportSerializer(serializers.ModelSerializer):
    school_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 
                 'is_active', 'date_joined', 'last_login', 'school_info']
    
    def get_school_info(self, obj):
        if obj.school:
            return {
                'id': obj.school.id,
                'name': obj.school.name,
                'subdomain': obj.school.subdomain
            }
        return None


class SectionReportSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name')
    subject_code = serializers.CharField(source='subject.subject_code')
    professor_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    avg_grade = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    late_submissions = serializers.SerializerMethodField()
    
    class Meta:
        model = Section
        fields = ['id', 'section_name', 'subject_name', 'subject_code', 
                 'professor_name', 'student_count', 'assignment_count', 
                 'avg_grade', 'completion_rate', 'late_submissions', 'created_at']
    
    def get_professor_name(self, obj):
        if obj.professor:
            return f"{obj.professor.first_name} {obj.professor.last_name}"
        return "No Professor"
    
    def get_student_count(self, obj):
        return obj.enrollments.filter(status='ENROLLED').count()
    
    def get_assignment_count(self, obj):
        return obj.assignments.count()
    
    def get_avg_grade(self, obj):
        submissions = Submission.objects.filter(
            assignment__section=obj,
            points_earned__isnull=False
        )
        if submissions.exists():
            total_points = sum(s.points_earned for s in submissions)
            total_possible = sum(s.assignment.total_points for s in submissions)
            return (total_points / total_possible * 100) if total_possible > 0 else 0
        return 0
    
    def get_completion_rate(self, obj):
        total_assignments = obj.assignments.count()
        total_students = obj.enrollments.filter(status='ENROLLED').count()
        if total_assignments > 0 and total_students > 0:
            total_expected = total_assignments * total_students
            completed = Submission.objects.filter(
                assignment__section=obj,
                status__in=['GRADED', 'RETURNED']
            ).count()
            return (completed / total_expected * 100) if total_expected > 0 else 0
        return 0
    
    def get_late_submissions(self, obj):
        from django.db import models
        return Submission.objects.filter(
            assignment__section=obj,
            submitted_at__gt=models.F('assignment__due_date')
        ).count()


class AssignmentReportSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.section_name')
    subject_name = serializers.CharField(source='section.subject.subject_name')
    professor_name = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    graded_count = serializers.SerializerMethodField()
    avg_grade = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    late_rate = serializers.SerializerMethodField()
    assignment_type = serializers.SerializerMethodField()
    max_points = serializers.DecimalField(source='total_points', max_digits=5, decimal_places=2)
    
    class Meta:
        model = Assignment
        fields = ['id', 'title', 'assignment_type', 'max_points', 'due_date', 
                 'section_name', 'subject_name', 'professor_name', 
                 'submission_count', 'graded_count', 'avg_grade', 
                 'completion_rate', 'late_rate', 'created_at']
    
    def get_professor_name(self, obj):
        if obj.section.professor:
            return f"{obj.section.professor.first_name} {obj.section.professor.last_name}"
        return "No Professor"
    
    def get_submission_count(self, obj):
        return obj.submissions.count()
    
    def get_graded_count(self, obj):
        return obj.submissions.filter(status__in=['GRADED', 'RETURNED']).count()
    
    def get_avg_grade(self, obj):
        submissions = obj.submissions.filter(points_earned__isnull=False)
        if submissions.exists():
            total_points = sum(s.points_earned for s in submissions)
            total_possible = submissions.count() * obj.total_points
            return (total_points / total_possible * 100) if total_possible > 0 else 0
        return 0
    
    def get_completion_rate(self, obj):
        total_students = obj.section.enrollments.filter(status='ENROLLED').count()
        submitted = obj.submissions.count()
        return (submitted / total_students * 100) if total_students > 0 else 0
    
    def get_late_rate(self, obj):
        total_submissions = obj.submissions.count()
        late_submissions = obj.submissions.filter(
            submitted_at__gt=obj.due_date
        ).count()
        return (late_submissions / total_submissions * 100) if total_submissions > 0 else 0
    
    def get_assignment_type(self, obj):
        # Determine assignment type based on title keywords
        title_lower = obj.title.lower()
        if 'homework' in title_lower or 'hw' in title_lower:
            return 'HOMEWORK'
        elif 'quiz' in title_lower:
            return 'QUIZ'
        elif 'exam' in title_lower or 'test' in title_lower:
            return 'EXAM'
        elif 'project' in title_lower:
            return 'PROJECT'
        elif 'discussion' in title_lower:
            return 'DISCUSSION'
        return 'HOMEWORK'  # Default


class GradeReportSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source='student.email')
    assignment_title = serializers.CharField(source='assignment.title')
    assignment_type = serializers.SerializerMethodField()
    section_name = serializers.CharField(source='assignment.section.section_name')
    subject_name = serializers.CharField(source='assignment.section.subject.subject_name')
    max_points = serializers.DecimalField(source='assignment.total_points', max_digits=5, decimal_places=2)
    percentage = serializers.SerializerMethodField()
    grade_letter = serializers.SerializerMethodField()
    is_late = serializers.SerializerMethodField()
    
    class Meta:
        model = Submission
        fields = ['id', 'student_name', 'student_email', 'assignment_title', 
                 'assignment_type', 'section_name', 'subject_name', 
                 'points_earned', 'max_points', 'percentage', 'grade_letter', 
                 'is_late', 'submitted_at', 'graded_at']
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"
    
    def get_assignment_type(self, obj):
        # Determine assignment type based on title keywords
        title_lower = obj.assignment.title.lower()
        if 'homework' in title_lower or 'hw' in title_lower:
            return 'HOMEWORK'
        elif 'quiz' in title_lower:
            return 'QUIZ'
        elif 'exam' in title_lower or 'test' in title_lower:
            return 'EXAM'
        elif 'project' in title_lower:
            return 'PROJECT'
        elif 'discussion' in title_lower:
            return 'DISCUSSION'
        return 'HOMEWORK'  # Default
    
    def get_percentage(self, obj):
        if obj.points_earned and obj.assignment.total_points:
            return (obj.points_earned / obj.assignment.total_points * 100)
        return 0
    
    def get_grade_letter(self, obj):
        percentage = self.get_percentage(obj)
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'
    
    def get_is_late(self, obj):
        if obj.submitted_at and obj.assignment.due_date:
            return obj.submitted_at > obj.assignment.due_date
        return False


class EnrollmentReportSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source='student.email')
    section_name = serializers.CharField(source='section.section_name')
    subject_name = serializers.CharField(source='section.subject.subject_name')
    subject_code = serializers.CharField(source='section.subject.subject_code')
    professor_name = serializers.SerializerMethodField()
    current_grade = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    completed_assignments = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = ['id', 'student_name', 'student_email', 'section_name', 
                 'subject_name', 'subject_code', 'professor_name', 
                 'enrollment_date', 'status', 'current_grade', 
                 'assignment_count', 'completed_assignments', 'completion_rate']
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"
    
    def get_professor_name(self, obj):
        if obj.section.professor:
            return f"{obj.section.professor.first_name} {obj.section.professor.last_name}"
        return "No Professor"
    
    def get_current_grade(self, obj):
        submissions = Submission.objects.filter(
            student=obj.student,
            assignment__section=obj.section,
            points_earned__isnull=False
        )
        if submissions.exists():
            total_points = sum(s.points_earned for s in submissions)
            total_possible = sum(s.assignment.total_points for s in submissions)
            return (total_points / total_possible * 100) if total_possible > 0 else 0
        return 0
    
    def get_assignment_count(self, obj):
        return obj.section.assignments.count()
    
    def get_completed_assignments(self, obj):
        return Submission.objects.filter(
            student=obj.student,
            assignment__section=obj.section,
            status__in=['GRADED', 'RETURNED']
        ).count()
    
    def get_completion_rate(self, obj):
        total_assignments = self.get_assignment_count(obj)
        completed = self.get_completed_assignments(obj)
        return (completed / total_assignments * 100) if total_assignments > 0 else 0


class SystemReportSerializer(serializers.Serializer):
    """System-wide report data (SuperAdmin only)"""
    total_schools = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_sections = serializers.IntegerField()
    total_assignments = serializers.IntegerField()
    total_submissions = serializers.IntegerField()
    total_grades = serializers.IntegerField()
    user_growth = serializers.ListField()
    grade_distribution = serializers.ListField()
    assignment_type_distribution = serializers.ListField()
    monthly_activity = serializers.ListField()