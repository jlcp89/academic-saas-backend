from django.db import models
from apps.users.models import User
from apps.organizations.models import School
from apps.academic.models import Assignment, Submission, Section, Subject
import json

class StudentLearningProfile(models.Model):
    """
    Perfil de aprendizaje individual de cada estudiante
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learning_profile')
    
    # Métricas de aprendizaje
    learning_style = models.CharField(max_length=50, null=True, blank=True)  # visual, auditory, kinesthetic
    pace_preference = models.CharField(max_length=20, null=True, blank=True)  # fast, moderate, slow
    difficulty_tolerance = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    
    # Patrones de comportamiento
    study_patterns = models.JSONField(default=dict)  # Horarios, duración, frecuencia
    engagement_metrics = models.JSONField(default=dict)  # Participación, tiempo en plataforma
    performance_trends = models.JSONField(default=dict)  # Evolución de calificaciones
    
    # Predicciones IA
    risk_level = models.CharField(max_length=20, default='LOW')  # LOW, MEDIUM, HIGH
    predicted_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    recommended_actions = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('school', 'student')
    
    def __str__(self):
        return f"Learning Profile - {self.student.username}"

class AssignmentIntelligence(models.Model):
    """
    Análisis de inteligencia de tareas y su efectividad
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    assignment = models.OneToOneField(Assignment, on_delete=models.CASCADE, related_name='intelligence')
    
    # Métricas de dificultad
    difficulty_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Análisis de patrones
    common_mistakes = models.JSONField(default=list)
    time_distribution = models.JSONField(default=dict)  # Tiempo promedio por estudiante
    success_factors = models.JSONField(default=list)
    
    # Recomendaciones IA
    optimization_suggestions = models.JSONField(default=list)
    difficulty_adjustment = models.CharField(max_length=20, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"AI Analysis - {self.assignment.title}"

class PredictiveAlert(models.Model):
    """
    Alertas predictivas basadas en IA
    """
    class AlertType(models.TextChoices):
        ACADEMIC_RISK = 'ACADEMIC_RISK', 'Academic Risk'
        ENGAGEMENT_DROP = 'ENGAGEMENT_DROP', 'Engagement Drop'
        PERFORMANCE_TREND = 'PERFORMANCE_TREND', 'Performance Trend'
        ASSIGNMENT_OVERDUE = 'ASSIGNMENT_OVERDUE', 'Assignment Overdue'
        LEARNING_GAP = 'LEARNING_GAP', 'Learning Gap'
    
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'
    
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictive_alerts')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    
    # Datos de la alerta
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)  # 0.00 - 1.00
    predicted_outcome = models.TextField()
    recommended_actions = models.JSONField(default=list)
    supporting_evidence = models.JSONField(default=dict)
    
    # Estado de la alerta
    is_active = models.BooleanField(default=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-confidence_score', '-created_at']
    
    def __str__(self):
        return f"{self.alert_type} - {self.student.username} ({self.priority})"

class LearningRecommendation(models.Model):
    """
    Recomendaciones personalizadas de aprendizaje
    """
    class RecommendationType(models.TextChoices):
        STUDY_RESOURCE = 'STUDY_RESOURCE', 'Study Resource'
        PRACTICE_EXERCISE = 'PRACTICE_EXERCISE', 'Practice Exercise'
        PEER_COLLABORATION = 'PEER_COLLABORATION', 'Peer Collaboration'
        TEACHER_CONSULTATION = 'TEACHER_CONSULTATION', 'Teacher Consultation'
        LEARNING_STRATEGY = 'LEARNING_STRATEGY', 'Learning Strategy'
    
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_recommendations')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    
    recommendation_type = models.CharField(max_length=20, choices=RecommendationType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Datos de la recomendación
    expected_impact = models.DecimalField(max_digits=3, decimal_places=2)  # 0.00 - 1.00
    time_requirement = models.CharField(max_length=50)  # "30 minutes", "2 hours"
    difficulty_level = models.CharField(max_length=20)  # "Easy", "Medium", "Hard"
    
    # Recursos y enlaces
    resources = models.JSONField(default=list)  # URLs, documentos, etc.
    related_assignments = models.ManyToManyField(Assignment, blank=True)
    
    # Seguimiento
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    student_feedback = models.TextField(null=True, blank=True)
    effectiveness_rating = models.IntegerField(null=True, blank=True)  # 1-5 stars
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-expected_impact', '-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.student.username}"

class AITrainingSession(models.Model):
    """
    Sesiones de entrenamiento y mejora de modelos de IA
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    
    session_name = models.CharField(max_length=255)
    model_type = models.CharField(max_length=100)  # "grade_prediction", "risk_assessment", etc.
    
    # Datos de entrenamiento
    training_data_size = models.IntegerField()
    validation_accuracy = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    test_accuracy = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    
    # Configuración del modelo
    model_parameters = models.JSONField(default=dict)
    feature_importance = models.JSONField(default=dict)
    
    # Estado
    is_active = models.BooleanField(default=False)
    deployment_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.session_name} - {self.model_type}"

class AcademicRiskPrediction(models.Model):
    """
    Predicción de riesgo académico para estudiantes
    """
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Low Risk'
        MEDIUM = 'MEDIUM', 'Medium Risk'
        HIGH = 'HIGH', 'High Risk'
        CRITICAL = 'CRITICAL', 'Critical Risk'
    
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='risk_predictions')
    
    # Predicción principal
    risk_score = models.DecimalField(max_digits=3, decimal_places=2)  # 0.00 - 1.00
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices)
    confidence = models.DecimalField(max_digits=3, decimal_places=2)  # 0.00 - 1.00
    
    # Factores de riesgo
    factors = models.JSONField(default=dict)  # Factores que contribuyen al riesgo
    predicted_outcome = models.TextField()  # Descripción del resultado predicho
    
    # Métricas específicas
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    assignment_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    late_submissions_count = models.IntegerField(default=0)
    participation_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    study_time_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    previous_semester_gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    current_semester_gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    days_since_last_login = models.IntegerField(default=0)
    
    # Estado y seguimiento
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('school', 'student')
        ordering = ['-risk_score', '-last_updated']
    
    def __str__(self):
        return f"Risk Prediction - {self.student.username} ({self.risk_level})"
    
    def get_risk_color(self):
        """Retorna el color CSS para el nivel de riesgo"""
        colors = {
            'LOW': 'green',
            'MEDIUM': 'yellow', 
            'HIGH': 'orange',
            'CRITICAL': 'red'
        }
        return colors.get(self.risk_level, 'gray')
    
    def get_risk_percentage(self):
        """Retorna el porcentaje de riesgo"""
        return int(self.risk_score * 100)
    
    def get_primary_factors(self):
        """Retorna los factores principales de riesgo"""
        if isinstance(self.factors, dict):
            return list(self.factors.keys())[:3]  # Top 3 factores
        return [] 