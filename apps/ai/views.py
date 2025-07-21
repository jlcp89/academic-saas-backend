from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    AcademicRiskPrediction, 
    StudentLearningProfile, 
    LearningRecommendation,
    PredictiveAlert,
    AssignmentIntelligence
)
from .serializers import (
    AcademicRiskPredictionSerializer,
    StudentLearningProfileSerializer,
    LearningRecommendationSerializer,
    PredictiveAlertSerializer,
    AssignmentIntelligenceSerializer,
    RiskDashboardSerializer,
    StudentRiskSummarySerializer
)
from apps.permissions import IsStudent, IsProfessor, IsSchoolAdmin, IsSameSchool
from apps.base import TenantAwareViewSet
from apps.users.models import User
from apps.academic.models import Section, Enrollment
from apps.organizations.models import School
from .tasks import calculate_student_risk, update_all_risk_predictions
from .ml_models import DataCollector
import logging

logger = logging.getLogger(__name__)

class AcademicRiskViewSet(TenantAwareViewSet):
    """
    ViewSet para gestión de predicciones de riesgo académico
    """
    queryset = AcademicRiskPrediction.objects.all()
    serializer_class = AcademicRiskPredictionSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsSchoolAdmin]
        else:
            permission_classes = [IsAuthenticated, IsSameSchool]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrar por rol del usuario
        if user.role == User.Role.STUDENT:
            queryset = queryset.filter(student=user)
        elif user.role == User.Role.PROFESSOR:
            # Profesores ven estudiantes de sus secciones
            professor_sections = Section.objects.filter(professor=user)
            student_ids = Enrollment.objects.filter(
                section__in=professor_sections
            ).values_list('student_id', flat=True)
            queryset = queryset.filter(student_id__in=student_ids)
        
        return queryset.filter(is_active=True)
    
    @action(detail=False, methods=['get'])
    def my_risk(self, request):
        """
        Obtener predicción de riesgo del usuario actual (estudiante)
        """
        if request.user.role != User.Role.STUDENT:
            return Response(
                {'error': 'Only students can access their own risk prediction'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            risk_prediction = AcademicRiskPrediction.objects.get(
                student=request.user,
                is_active=True
            )
            serializer = self.get_serializer(risk_prediction)
            return Response(serializer.data)
        except AcademicRiskPrediction.DoesNotExist:
            # Calcular riesgo si no existe
            calculate_student_risk.delay(request.user.id)
            return Response(
                {'message': 'Risk prediction is being calculated. Please check back in a few minutes.'},
                status=status.HTTP_202_ACCEPTED
            )
    
    @action(detail=False, methods=['post'])
    def calculate_risk(self, request):
        """
        Calcular riesgo para un estudiante específico
        """
        if request.user.role not in [User.Role.PROFESSOR, User.Role.ADMIN]:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student_id = request.data.get('student_id')
        if not student_id:
            return Response(
                {'error': 'student_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = User.objects.get(id=student_id, role='STUDENT')
            
            # Verificar que el estudiante pertenece a la misma escuela
            if student.school != request.user.school:
                return Response(
                    {'error': 'Student not found in your school'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Iniciar cálculo de riesgo
            calculate_student_risk.delay(student_id)
            
            return Response({
                'message': f'Risk calculation started for student {student.username}',
                'student_id': student_id
            }, status=status.HTTP_202_ACCEPTED)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def update_all(self, request):
        """
        Actualizar predicciones de riesgo para todos los estudiantes
        """
        if request.user.role not in [User.Role.ADMIN]:
            return Response(
                {'error': 'Only school admins can update all predictions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Iniciar actualización masiva
        update_all_risk_predictions.delay()
        
        return Response({
            'message': 'Bulk risk prediction update started'
        }, status=status.HTTP_202_ACCEPTED)

class RiskDashboardViewSet(ViewSet):
    """
    ViewSet para dashboards de riesgo
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def class_overview(self, request, section_id=None):
        """
        Vista de riesgo para una clase específica
        """
        if request.user.role not in [User.Role.PROFESSOR, User.Role.ADMIN]:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Obtener sección
            if section_id:
                section = get_object_or_404(Section, id=section_id, school=request.user.school)
            else:
                # Si no se especifica sección, usar la primera del profesor
                if request.user.role == User.Role.PROFESSOR:
                    section = Section.objects.filter(professor=request.user).first()
                else:
                    section = Section.objects.filter(school=request.user.school).first()
            
            if not section:
                return Response(
                    {'error': 'No sections found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Obtener estudiantes de la sección
            enrollments = Enrollment.objects.filter(
                section=section,
                status='ENROLLED'
            )
            students = [enrollment.student for enrollment in enrollments]
            
            # Obtener predicciones de riesgo
            risk_predictions = AcademicRiskPrediction.objects.filter(
                student__in=students,
                is_active=True
            ).order_by('-risk_score')
            
            # Calcular estadísticas
            total_students = len(students)
            high_risk_students = risk_predictions.filter(
                risk_level__in=['HIGH', 'CRITICAL']
            )
            
            risk_distribution = {
                'LOW': risk_predictions.filter(risk_level='LOW').count(),
                'MEDIUM': risk_predictions.filter(risk_level='MEDIUM').count(),
                'HIGH': risk_predictions.filter(risk_level='HIGH').count(),
                'CRITICAL': risk_predictions.filter(risk_level='CRITICAL').count(),
            }
            
            average_risk_score = risk_predictions.aggregate(
                avg_risk=Avg('risk_score')
            )['avg_risk'] or 0
            
            # Análisis de tendencias (simulado)
            trend_analysis = {
                'trend': 'increasing',
                'change_percentage': 15.5,
                'period': 'last_30_days'
            }
            
            # Preparar datos para el serializer
            dashboard_data = {
                'total_students': total_students,
                'high_risk_count': high_risk_students.count(),
                'risk_distribution': risk_distribution,
                'high_risk_students': AcademicRiskPredictionSerializer(
                    high_risk_students[:10], many=True
                ).data,
                'average_risk_score': average_risk_score,
                'trend_analysis': trend_analysis
            }
            
            serializer = RiskDashboardSerializer(dashboard_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in class overview: {e}")
            return Response(
                {'error': 'Error generating class overview'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def student_summary(self, request, student_id=None):
        """
        Resumen completo de riesgo para un estudiante
        """
        if request.user.role not in [User.Role.PROFESSOR, User.Role.ADMIN, User.Role.STUDENT]:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Determinar estudiante
            if student_id and request.user.role in [User.Role.PROFESSOR, User.Role.ADMIN]:
                student = get_object_or_404(User, id=student_id, role='STUDENT')
                if student.school != request.user.school:
                    return Response(
                        {'error': 'Student not found in your school'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                student = request.user
            
            # Obtener predicción de riesgo
            try:
                risk_prediction = AcademicRiskPrediction.objects.get(
                    student=student,
                    is_active=True
                )
            except AcademicRiskPrediction.DoesNotExist:
                # Calcular riesgo si no existe
                calculate_student_risk.delay(student.id)
                return Response(
                    {'message': 'Risk prediction is being calculated. Please check back in a few minutes.'},
                    status=status.HTTP_202_ACCEPTED
                )
            
            # Obtener recomendaciones recientes
            recent_recommendations = LearningRecommendation.objects.filter(
                student=student,
                is_completed=False
            ).order_by('-expected_impact', '-created_at')[:5]
            
            # Obtener alertas activas
            active_alerts = PredictiveAlert.objects.filter(
                student=student,
                is_active=True
            ).order_by('-priority', '-created_at')[:5]
            
            # Análisis de tendencia de rendimiento (simulado)
            performance_trend = {
                'current_period': 'Q1 2024',
                'previous_period': 'Q4 2023',
                'change_percentage': 5.2,
                'trend': 'improving',
                'subjects': [
                    {'name': 'Mathematics', 'change': 8.5},
                    {'name': 'Science', 'change': -2.1},
                    {'name': 'History', 'change': 12.3}
                ]
            }
            
            # Sugerencias de mejora
            improvement_suggestions = [
                "Revisar conceptos fundamentales de matemáticas",
                "Participar más en las discusiones de clase",
                "Completar tareas antes de la fecha límite",
                "Formar grupos de estudio con compañeros"
            ]
            
            # Preparar datos para el serializer
            summary_data = {
                'risk_prediction': AcademicRiskPredictionSerializer(risk_prediction).data,
                'recent_recommendations': LearningRecommendationSerializer(
                    recent_recommendations, many=True
                ).data,
                'active_alerts': PredictiveAlertSerializer(
                    active_alerts, many=True
                ).data,
                'performance_trend': performance_trend,
                'improvement_suggestions': improvement_suggestions
            }
            
            serializer = StudentRiskSummarySerializer(summary_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in student summary: {e}")
            return Response(
                {'error': 'Error generating student summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStudent])
def student_risk_dashboard(request):
    """
    Dashboard de riesgo para estudiantes
    """
    try:
        # Obtener predicción de riesgo del estudiante
        try:
            risk_prediction = AcademicRiskPrediction.objects.get(
                student=request.user,
                is_active=True
            )
        except AcademicRiskPrediction.DoesNotExist:
            # Calcular riesgo si no existe
            calculate_student_risk.delay(request.user.id)
            return Response({
                'message': 'Risk prediction is being calculated. Please check back in a few minutes.',
                'status': 'calculating'
            }, status=status.HTTP_202_ACCEPTED)
        
        # Obtener recomendaciones recientes
        recent_recommendations = LearningRecommendation.objects.filter(
            student=request.user,
            is_completed=False
        ).order_by('-expected_impact', '-created_at')[:5]
        
        # Obtener alertas activas
        active_alerts = PredictiveAlert.objects.filter(
            student=request.user,
            is_active=True
        ).order_by('-priority', '-created_at')[:3]
        
        return Response({
            'risk_prediction': AcademicRiskPredictionSerializer(risk_prediction).data,
            'recent_recommendations': LearningRecommendationSerializer(
                recent_recommendations, many=True
            ).data,
            'active_alerts': PredictiveAlertSerializer(
                active_alerts, many=True
            ).data,
            'status': 'ready'
        })
        
    except Exception as e:
        logger.error(f"Error in student risk dashboard: {e}")
        return Response(
            {'error': 'Error loading risk dashboard'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudent])
def mark_recommendation_completed(request, recommendation_id):
    """
    Marcar una recomendación como completada
    """
    try:
        recommendation = get_object_or_404(
            LearningRecommendation,
            id=recommendation_id,
            student=request.user
        )
        
        recommendation.is_completed = True
        recommendation.completed_at = timezone.now()
        recommendation.student_feedback = request.data.get('feedback', '')
        recommendation.effectiveness_rating = request.data.get('rating')
        recommendation.save()
        
        return Response({
            'message': 'Recommendation marked as completed',
            'recommendation': LearningRecommendationSerializer(recommendation).data
        })
        
    except Exception as e:
        logger.error(f"Error marking recommendation as completed: {e}")
        return Response(
            {'error': 'Error updating recommendation'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def acknowledge_alert(request, alert_id):
    """
    Reconocer una alerta predictiva
    """
    try:
        alert = get_object_or_404(
            PredictiveAlert,
            id=alert_id,
            is_active=True
        )
        
        # Verificar permisos
        if request.user.role == User.Role.STUDENT and alert.student != request.user:
            return Response(
                {'error': 'You can only acknowledge your own alerts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        return Response({
            'message': 'Alert acknowledged',
            'alert': PredictiveAlertSerializer(alert).data
        })
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return Response(
            {'error': 'Error acknowledging alert'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 