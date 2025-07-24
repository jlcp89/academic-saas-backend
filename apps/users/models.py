from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.organizations.models import School

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'Superadmin'
        ADMIN = 'ADMIN', 'School Admin'
        PROFESSOR = 'PROFESSOR', 'Professor'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(max_length=10, choices=Role.choices, null=False, blank=False)
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)