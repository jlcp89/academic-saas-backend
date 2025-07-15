from django.db import models
from apps.users.models import User
from apps.organizations.models import School

class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    subject_name = models.CharField(max_length=255)
    subject_code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('school', 'subject_code')
        ordering = ['subject_code']
    
    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"

class Section(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    section_name = models.CharField(max_length=100)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='sections')
    professor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='taught_sections')
    start_date = models.DateField()
    end_date = models.DateField()
    max_students = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('school', 'section_name', 'subject')
        ordering = ['section_name']
    
    def __str__(self):
        return f"{self.section_name} - {self.subject.subject_code}"

class Enrollment(models.Model):
    class StatusChoices(models.TextChoices):
        ENROLLED = 'ENROLLED', 'Enrolled'
        DROPPED = 'DROPPED', 'Dropped'
        COMPLETED = 'COMPLETED', 'Completed'
    
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.ENROLLED)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=2, null=True, blank=True)
    
    class Meta:
        unique_together = ('school', 'student', 'section')
    
    def __str__(self):
        return f"{self.student.username} - {self.section.section_name}"

class Assignment(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateTimeField()
    total_points = models.DecimalField(max_digits=5, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_assignments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-due_date']
    
    def __str__(self):
        return f"{self.title} - {self.section.section_name}"

class Submission(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        GRADED = 'GRADED', 'Graded'
        RETURNED = 'RETURNED', 'Returned'
    
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.DRAFT)
    content = models.TextField()
    file_url = models.URLField(max_length=500, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_submissions')
    graded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('school', 'assignment', 'student')
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"