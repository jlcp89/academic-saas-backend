from rest_framework import serializers
from django.db.models import Avg, Sum, Count
from apps.users.models import User
from apps.academic.models import Section, Assignment, Submission, Enrollment
from apps.organizations.models import School


class UserReportSerializer(serializers.ModelSerializer):
    school_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 
            'role', 'is_active', 'date_joined', 'last_login', 'school_info'
        ]
    
    def get_school_info(self, obj):
        if hasattr(obj, 'school') and obj.school:
            return {
                'id': obj.school.id,
                'name': obj.school.name,
                'subdomain': obj.school.subdomain
            }
        return None


class SectionReportSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)
    professor_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    avg_grade = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    late_submissions = serializers.SerializerMethodField()
    
    class Meta:
        model = Section
        fields = [
            'id', 'section_name', 'subject_name', 'subject_code', 
            'professor_name', 'student_count', 'assignment_count',
            'avg_grade', 'completion_rate', 'late_submissions', 'created_at'
        ]
    
    def get_professor_name(self, obj):
        if obj.professor:
            return f"{obj.professor.first_name} {obj.professor.last_name}"
        return None
    
    def get_student_count(self, obj):
        return obj.enrollments.filter(status='ENROLLED').count()
    
    def get_assignment_count(self, obj):
        return obj.assignments.count()
    
    def get_avg_grade(self, obj):
        submissions = Submission.objects.filter(
            assignment__section=obj,
            status='GRADED',
            points_earned__isnull=False
        )
        if submissions.exists():
            return submissions.aggregate(avg=Avg('points_earned'))['avg'] or 0
        return 0
    
    def get_completion_rate(self, obj):
        assignments = obj.assignments.all()
        if not assignments.exists():
            return 0
        
        total_possible = assignments.count() * self.get_student_count(obj)
        if total_possible == 0:
            return 0
        
        total_submissions = sum(
            assignment.submissions.filter(status__in=['SUBMITTED', 'GRADED']).count() 
            for assignment in assignments
        )
        return round((total_submissions / total_possible) * 100, 2)
    
    def get_late_submissions(self, obj):
        late_count = 0
        for assignment in obj.assignments.all():
            late_count += assignment.submissions.filter(
                submitted_at__gt=assignment.due_date
            ).count()
        return late_count


class AssignmentReportSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.section_name', read_only=True)
    subject_name = serializers.CharField(source='section.subject.subject_name', read_only=True)
    professor_name = serializers.SerializerMethodField()
    max_points = serializers.CharField(source='total_points', read_only=True)
    submission_count = serializers.SerializerMethodField()
    graded_count = serializers.SerializerMethodField()
    avg_grade = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    late_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'max_points', 'due_date',
            'section_name', 'subject_name', 'professor_name', 'submission_count',
            'graded_count', 'avg_grade', 'completion_rate', 'late_rate', 'created_at'
        ]
    
    def get_professor_name(self, obj):
        if obj.section and obj.section.professor:
            prof = obj.section.professor
            return f"{prof.first_name} {prof.last_name}"
        return None
    
    def get_submission_count(self, obj):
        return obj.submissions.filter(status__in=['SUBMITTED', 'GRADED']).count()
    
    def get_graded_count(self, obj):
        return obj.submissions.filter(status='GRADED').count()
    
    def get_avg_grade(self, obj):
        graded_submissions = obj.submissions.filter(
            status='GRADED',
            points_earned__isnull=False
        )
        if graded_submissions.exists():
            return graded_submissions.aggregate(avg=Avg('points_earned'))['avg'] or 0
        return 0
    
    def get_completion_rate(self, obj):
        enrolled_students = obj.section.enrollments.filter(status='ENROLLED').count()
        if enrolled_students == 0:
            return 0
        submission_count = self.get_submission_count(obj)
        return round((submission_count / enrolled_students) * 100, 2)
    
    def get_late_rate(self, obj):
        total_submissions = self.get_submission_count(obj)
        if total_submissions == 0:
            return 0
        late_submissions = obj.submissions.filter(
            submitted_at__gt=obj.due_date
        ).count()
        return round((late_submissions / total_submissions) * 100, 2)


class SubmissionReportSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source='student.email', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    assignment_type = serializers.SerializerMethodField()
    section_name = serializers.CharField(source='assignment.section.section_name', read_only=True)
    subject_name = serializers.CharField(source='assignment.section.subject.subject_name', read_only=True)
    max_points = serializers.CharField(source='assignment.total_points', read_only=True)
    percentage = serializers.SerializerMethodField()
    grade_letter = serializers.SerializerMethodField()
    is_late = serializers.SerializerMethodField()
    
    class Meta:
        model = Submission
        fields = [
            'id', 'student_name', 'student_email', 'assignment_title', 'assignment_type',
            'section_name', 'subject_name', 'points_earned', 'max_points',
            'percentage', 'grade_letter', 'is_late',
            'submitted_at', 'graded_at'
        ]
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"
    
    def get_assignment_type(self, obj):
        # Since assignment_type doesn't exist, we'll return a default value
        return "ASSIGNMENT"
    
    def get_percentage(self, obj):
        if obj.assignment.total_points > 0 and obj.points_earned is not None:
            return round((float(obj.points_earned) / float(obj.assignment.total_points)) * 100, 2)
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
    student_email = serializers.CharField(source='student.email', read_only=True)
    section_name = serializers.CharField(source='section.section_name', read_only=True)
    subject_name = serializers.CharField(source='section.subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='section.subject.subject_code', read_only=True)
    professor_name = serializers.SerializerMethodField()
    current_grade = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    completed_assignments = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'student_name', 'student_email', 'section_name',
            'subject_name', 'subject_code', 'professor_name', 'enrollment_date',
            'status', 'current_grade', 'assignment_count', 'completed_assignments',
            'completion_rate'
        ]
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"
    
    def get_professor_name(self, obj):
        if obj.section.professor:
            prof = obj.section.professor
            return f"{prof.first_name} {prof.last_name}"
        return None
    
    def get_current_grade(self, obj):
        submissions = Submission.objects.filter(
            student=obj.student,
            assignment__section=obj.section,
            status='GRADED',
            points_earned__isnull=False
        )
        if submissions.exists():
            total_points = submissions.aggregate(
                earned=Sum('points_earned'),
                possible=Sum('assignment__total_points')
            )
            if total_points['possible'] and total_points['possible'] > 0:
                return round((float(total_points['earned']) / float(total_points['possible'])) * 100, 2)
        return 0
    
    def get_assignment_count(self, obj):
        return obj.section.assignments.count()
    
    def get_completed_assignments(self, obj):
        return Submission.objects.filter(
            student=obj.student,
            assignment__section=obj.section,
            status='GRADED'
        ).count()
    
    def get_completion_rate(self, obj):
        assignment_count = self.get_assignment_count(obj)
        if assignment_count == 0:
            return 0
        completed = self.get_completed_assignments(obj)
        return round((completed / assignment_count) * 100, 2)