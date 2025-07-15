from django.db import models

class School(models.Model):
    """
    Represents a tenant in our SaaS system. Each School is a customer.
    """
    name = models.CharField(max_length=255, unique=True)
    subdomain = models.CharField(max_length=100, unique=True, help_text="e.g., 'highschool-xyz' for highschool-xyz.myapp.com")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Subscription(models.Model):
    """
    Manages the subscription status for each School.
    """
    class PlanChoices(models.TextChoices):
        BASIC = 'BASIC', 'Basic'
        PREMIUM = 'PREMIUM', 'Premium'

    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELED = 'CANCELED', 'Canceled'

    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=10, choices=PlanChoices.choices, default=PlanChoices.BASIC)
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    end_date = models.DateField()

    def __str__(self):
        return f"{self.school.name} Subscription - {self.plan} Plan"