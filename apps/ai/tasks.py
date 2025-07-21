from celery import shared_task
from django.utils import timezone
from django.db import models
from .models import AcademicRiskPrediction, LearningRecommendation, PredictiveAlert
from .ml_models import AcademicRiskPredictor, DataCollector
from apps.users.models import User
from apps.organizations.models import School
from apps.academic.models import Assignment, Submission, Enrollment
import logging

logger = logging.getLogger(__name__)

@shared_task
def calculate_student_risk(student_id):
    """
    Calcular riesgo académico para un estudiante específico
    """
    try:
        student = User.objects.get(id=student_id, role='STUDENT')
        school = student.school
        
        if not school:
            logger.warning(f"Student {student_id} has no school assigned")
            return None
        
        # Recopilar datos del estudiante
        student_data = DataCollector.collect_student_data(student, school)
        
        if not student_data:
            logger.warning(f"No data available for student {student_id}")
            return None
        
        # Inicializar predictor
        predictor = AcademicRiskPredictor()
        
        # Predecir riesgo
        prediction = predictor.predict_risk(student_data)
        
        # Guardar predicción en base de datos
        risk_prediction, created = AcademicRiskPrediction.objects.update_or_create(
            school=school,
            student=student,
            defaults={
                'risk_score': prediction['risk_score'],
                'risk_level': prediction['risk_level'],
                'confidence': prediction['confidence'],
                'factors': prediction['factors'],
                'predicted_outcome': prediction['predicted_outcome'],
                'attendance_rate': student_data.get('attendance_rate'),
                'assignment_completion_rate': student_data.get('assignment_completion_rate'),
                'average_grade': student_data.get('average_grade'),
                'late_submissions_count': int(student_data.get('late_submissions_rate', 0) * 100),
                'participation_score': student_data.get('participation_score'),
                'study_time_hours': student_data.get('study_time_hours'),
                'previous_semester_gpa': student_data.get('previous_semester_gpa'),
                'current_semester_gpa': student_data.get('current_semester_gpa'),
                'days_since_last_login': student_data.get('days_since_last_login'),
                'is_active': True
            }
        )
        
        # Crear alerta si el riesgo es alto o crítico
        if prediction['risk_level'] in ['HIGH', 'CRITICAL']:
            create_risk_alert.delay(student_id, prediction)
        
        # Generar recomendaciones si es necesario
        if prediction['risk_level'] in ['MEDIUM', 'HIGH', 'CRITICAL']:
            generate_learning_recommendations.delay(student_id, prediction)
        
        logger.info(f"Risk calculation completed for student {student_id}: {prediction['risk_level']}")
        return prediction
        
    except User.DoesNotExist:
        logger.error(f"Student {student_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error calculating risk for student {student_id}: {e}")
        return None

@shared_task
def update_all_risk_predictions():
    """
    Actualizar predicciones de riesgo para todos los estudiantes
    """
    try:
        students = User.objects.filter(role='STUDENT', school__isnull=False)
        total_students = students.count()
        updated_count = 0
        
        logger.info(f"Starting risk prediction update for {total_students} students")
        
        for student in students:
            try:
                result = calculate_student_risk.delay(student.id)
                if result:
                    updated_count += 1
            except Exception as e:
                logger.error(f"Error updating risk for student {student.id}: {e}")
        
        logger.info(f"Risk prediction update completed: {updated_count}/{total_students} students updated")
        return {
            'total_students': total_students,
            'updated_count': updated_count,
            'success_rate': updated_count / total_students if total_students > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error in bulk risk prediction update: {e}")
        return None

@shared_task
def create_risk_alert(student_id, prediction):
    """
    Crear alerta de riesgo para un estudiante
    """
    try:
        student = User.objects.get(id=student_id, role='STUDENT')
        school = student.school
        
        # Determinar prioridad basada en nivel de riesgo
        priority_mapping = {
            'HIGH': PredictiveAlert.Priority.HIGH,
            'CRITICAL': PredictiveAlert.Priority.CRITICAL
        }
        
        priority = priority_mapping.get(prediction['risk_level'], PredictiveAlert.Priority.MEDIUM)
        
        # Crear alerta
        alert = PredictiveAlert.objects.create(
            school=school,
            student=student,
            alert_type=PredictiveAlert.AlertType.ACADEMIC_RISK,
            priority=priority,
            confidence_score=prediction['confidence'],
            predicted_outcome=prediction['predicted_outcome'],
            recommended_actions=prediction.get('factors', {}),
            supporting_evidence=prediction.get('factors', {}),
            is_active=True
        )
        
        logger.info(f"Risk alert created for student {student_id}: {priority}")
        return alert.id
        
    except Exception as e:
        logger.error(f"Error creating risk alert for student {student_id}: {e}")
        return None

@shared_task
def generate_learning_recommendations(student_id, prediction):
    """
    Generar recomendaciones de aprendizaje personalizadas
    """
    try:
        student = User.objects.get(id=student_id, role='STUDENT')
        school = student.school
        
        # Obtener materias del estudiante
        enrollments = Enrollment.objects.filter(
            student=student,
            school=school,
            status='ENROLLED'
        )
        
        recommendations_created = 0
        
        for enrollment in enrollments:
            subject = enrollment.section.subject
            
            # Generar recomendaciones basadas en factores de riesgo
            factors = prediction.get('factors', {})
            
            if 'Calificaciones bajas' in factors:
                # Recomendación para mejorar calificaciones
                recommendation = LearningRecommendation.objects.create(
                    school=school,
                    student=student,
                    subject=subject,
                    recommendation_type=LearningRecommendation.RecommendationType.STUDY_RESOURCE,
                    title=f"Mejorar calificaciones en {subject.subject_name}",
                    description="Basado en tu rendimiento actual, te recomendamos revisar los conceptos fundamentales y practicar con ejercicios adicionales.",
                    expected_impact=0.7,
                    time_requirement="1-2 horas por semana",
                    difficulty_level="Medium",
                    resources=[
                        {"type": "video", "url": "https://example.com/tutorial", "title": "Tutorial básico"},
                        {"type": "exercise", "url": "https://example.com/practice", "title": "Ejercicios de práctica"}
                    ]
                )
                recommendations_created += 1
            
            if 'Tareas incompletas' in factors:
                # Recomendación para completar tareas
                recommendation = LearningRecommendation.objects.create(
                    school=school,
                    student=student,
                    subject=subject,
                    recommendation_type=LearningRecommendation.RecommendationType.LEARNING_STRATEGY,
                    title=f"Organizar tiempo para tareas en {subject.subject_name}",
                    description="Te recomendamos crear un calendario de estudio y establecer recordatorios para completar las tareas a tiempo.",
                    expected_impact=0.8,
                    time_requirement="30 minutos de planificación",
                    difficulty_level="Easy",
                    resources=[
                        {"type": "tool", "url": "https://example.com/calendar", "title": "Calendario de estudio"},
                        {"type": "guide", "url": "https://example.com/time-management", "title": "Guía de gestión del tiempo"}
                    ]
                )
                recommendations_created += 1
            
            if 'Baja participación' in factors:
                # Recomendación para aumentar participación
                recommendation = LearningRecommendation.objects.create(
                    school=school,
                    student=student,
                    subject=subject,
                    recommendation_type=LearningRecommendation.RecommendationType.PEER_COLLABORATION,
                    title=f"Aumentar participación en {subject.subject_name}",
                    description="Te recomendamos participar más en las discusiones de clase y formar grupos de estudio con compañeros.",
                    expected_impact=0.6,
                    time_requirement="1 hora por semana",
                    difficulty_level="Easy",
                    resources=[
                        {"type": "guide", "url": "https://example.com/participation", "title": "Guía de participación efectiva"},
                        {"type": "group", "url": "https://example.com/study-groups", "title": "Grupos de estudio disponibles"}
                    ]
                )
                recommendations_created += 1
        
        logger.info(f"Generated {recommendations_created} learning recommendations for student {student_id}")
        return recommendations_created
        
    except Exception as e:
        logger.error(f"Error generating learning recommendations for student {student_id}: {e}")
        return 0

@shared_task
def analyze_assignment_intelligence(assignment_id):
    """
    Analizar inteligencia de una tarea específica
    """
    try:
        assignment = Assignment.objects.get(id=assignment_id)
        school = assignment.school
        
        # Obtener todas las submissions para esta tarea
        submissions = Submission.objects.filter(assignment=assignment)
        
        if not submissions.exists():
            logger.warning(f"No submissions found for assignment {assignment_id}")
            return None
        
        # Calcular métricas
        total_submissions = submissions.count()
        completed_submissions = submissions.filter(status='SUBMITTED').count()
        graded_submissions = submissions.filter(points_earned__isnull=False)
        
        # Tasa de completación
        completion_rate = completed_submissions / total_submissions if total_submissions > 0 else 0
        
        # Calificación promedio
        if graded_submissions.exists():
            average_grade = graded_submissions.aggregate(
                avg_grade=models.Avg('points_earned')
            )['avg_grade']
        else:
            average_grade = 0
        
        # Calcular dificultad basada en calificaciones
        if average_grade > 0:
            difficulty_score = 1 - (average_grade / assignment.total_points)
        else:
            difficulty_score = 0.5  # Dificultad media por defecto
        
        # Análisis de errores comunes (simulado)
        common_mistakes = [
            "Conceptos fundamentales no comprendidos",
            "Errores de cálculo",
            "Falta de atención a las instrucciones"
        ]
        
        # Distribución de tiempo (simulada)
        time_distribution = {
            "0-1 hour": 0.3,
            "1-3 hours": 0.4,
            "3-5 hours": 0.2,
            "5+ hours": 0.1
        }
        
        # Factores de éxito (simulados)
        success_factors = [
            "Revisión previa del material",
            "Participación en clase",
            "Consulta con el profesor"
        ]
        
        # Sugerencias de optimización
        optimization_suggestions = []
        if completion_rate < 0.7:
            optimization_suggestions.append("Considerar extender el plazo de entrega")
        if average_grade < assignment.total_points * 0.6:
            optimization_suggestions.append("Revisar la dificultad de la tarea")
        if difficulty_score > 0.8:
            optimization_suggestions.append("Proporcionar más recursos de apoyo")
        
        # Ajuste de dificultad sugerido
        difficulty_adjustment = None
        if difficulty_score > 0.8:
            difficulty_adjustment = "REDUCE"
        elif difficulty_score < 0.2:
            difficulty_adjustment = "INCREASE"
        
        # Guardar o actualizar análisis
        intelligence, created = AssignmentIntelligence.objects.update_or_create(
            school=school,
            assignment=assignment,
            defaults={
                'difficulty_score': difficulty_score,
                'completion_rate': completion_rate,
                'average_grade': average_grade,
                'common_mistakes': common_mistakes,
                'time_distribution': time_distribution,
                'success_factors': success_factors,
                'optimization_suggestions': optimization_suggestions,
                'difficulty_adjustment': difficulty_adjustment
            }
        )
        
        logger.info(f"Assignment intelligence analysis completed for assignment {assignment_id}")
        return {
            'assignment_id': assignment_id,
            'difficulty_score': difficulty_score,
            'completion_rate': completion_rate,
            'average_grade': average_grade,
            'optimization_suggestions': optimization_suggestions
        }
        
    except Assignment.DoesNotExist:
        logger.error(f"Assignment {assignment_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error analyzing assignment intelligence for {assignment_id}: {e}")
        return None

@shared_task
def cleanup_old_predictions():
    """
    Limpiar predicciones antiguas (más de 30 días)
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=30)
        
        # Desactivar predicciones antiguas
        old_predictions = AcademicRiskPrediction.objects.filter(
            last_updated__lt=cutoff_date,
            is_active=True
        )
        
        deactivated_count = old_predictions.update(is_active=False)
        
        # Limpiar alertas antiguas
        old_alerts = PredictiveAlert.objects.filter(
            created_at__lt=cutoff_date,
            is_active=True
        )
        
        archived_alerts = old_alerts.update(is_active=False)
        
        logger.info(f"Cleanup completed: {deactivated_count} predictions and {archived_alerts} alerts deactivated")
        return {
            'deactivated_predictions': deactivated_count,
            'archived_alerts': archived_alerts
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        return None 