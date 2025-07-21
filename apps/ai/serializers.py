from rest_framework import serializers
from .models import (
    AcademicRiskPrediction, 
    StudentLearningProfile, 
    LearningRecommendation,
    PredictiveAlert,
    AssignmentIntelligence
)

class AcademicRiskPredictionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    risk_percentage = serializers.SerializerMethodField()
    risk_color = serializers.SerializerMethodField()
    primary_factors = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademicRiskPrediction
        fields = [
            'id', 'student', 'student_name', 'student_email', 'risk_score', 
            'risk_level', 'confidence', 'factors', 'predicted_outcome',
            'attendance_rate', 'assignment_completion_rate', 'average_grade',
            'late_submissions_count', 'participation_score', 'study_time_hours',
            'previous_semester_gpa', 'current_semester_gpa', 'days_since_last_login',
            'risk_percentage', 'risk_color', 'primary_factors', 'is_active',
            'last_updated', 'created_at'
        ]
        read_only_fields = ['student', 'risk_score', 'risk_level', 'confidence', 
                           'factors', 'predicted_outcome', 'last_updated', 'created_at']
    
    def get_risk_percentage(self, obj):
        return obj.get_risk_percentage()
    
    def get_risk_color(self, obj):
        return obj.get_risk_color()
    
    def get_primary_factors(self, obj):
        return obj.get_primary_factors()

class StudentLearningProfileSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    
    class Meta:
        model = StudentLearningProfile
        fields = [
            'id', 'student', 'student_name', 'learning_style', 'pace_preference',
            'difficulty_tolerance', 'study_patterns', 'engagement_metrics',
            'performance_trends', 'risk_level', 'predicted_grade',
            'recommended_actions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['student', 'created_at', 'updated_at']

class LearningRecommendationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    expected_impact_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = LearningRecommendation
        fields = [
            'id', 'student', 'student_name', 'subject', 'subject_name',
            'recommendation_type', 'title', 'description', 'expected_impact',
            'expected_impact_percentage', 'time_requirement', 'difficulty_level',
            'resources', 'related_assignments', 'is_completed', 'completed_at',
            'student_feedback', 'effectiveness_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['student', 'created_at', 'updated_at']
    
    def get_expected_impact_percentage(self, obj):
        return int(obj.expected_impact * 100)

class PredictiveAlertSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.username', read_only=True)
    confidence_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = PredictiveAlert
        fields = [
            'id', 'student', 'student_name', 'subject', 'subject_name',
            'alert_type', 'priority', 'confidence_score', 'confidence_percentage',
            'predicted_outcome', 'recommended_actions', 'supporting_evidence',
            'is_active', 'acknowledged_by', 'acknowledged_by_name',
            'acknowledged_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['student', 'created_at', 'updated_at']
    
    def get_confidence_percentage(self, obj):
        return int(obj.confidence_score * 100)

class AssignmentIntelligenceSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    subject_name = serializers.CharField(source='assignment.section.subject.subject_name', read_only=True)
    completion_rate_percentage = serializers.SerializerMethodField()
    difficulty_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = AssignmentIntelligence
        fields = [
            'id', 'assignment', 'assignment_title', 'subject_name',
            'difficulty_score', 'difficulty_percentage', 'completion_rate',
            'completion_rate_percentage', 'average_grade', 'common_mistakes',
            'time_distribution', 'success_factors', 'optimization_suggestions',
            'difficulty_adjustment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['assignment', 'created_at', 'updated_at']
    
    def get_completion_rate_percentage(self, obj):
        if obj.completion_rate:
            return int(obj.completion_rate)
        return 0
    
    def get_difficulty_percentage(self, obj):
        if obj.difficulty_score:
            return int(obj.difficulty_score * 100)
        return 0

class RiskDashboardSerializer(serializers.Serializer):
    """Serializer para el dashboard de riesgo de una clase"""
    total_students = serializers.IntegerField()
    high_risk_count = serializers.IntegerField()
    risk_distribution = serializers.DictField()
    high_risk_students = AcademicRiskPredictionSerializer(many=True)
    average_risk_score = serializers.DecimalField(max_digits=3, decimal_places=2)
    trend_analysis = serializers.DictField()

class StudentRiskSummarySerializer(serializers.Serializer):
    """Serializer para resumen de riesgo de un estudiante"""
    risk_prediction = AcademicRiskPredictionSerializer()
    recent_recommendations = LearningRecommendationSerializer(many=True)
    active_alerts = PredictiveAlertSerializer(many=True)
    performance_trend = serializers.DictField()
    improvement_suggestions = serializers.ListField() 