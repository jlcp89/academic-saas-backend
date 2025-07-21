#!/usr/bin/env python
"""
Script para crear datos de prueba para el sistema de predicción de riesgo académico
"""
import os
import sys
import django
from datetime import datetime, timedelta
import random

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User, School
from apps.academic.models import Subject, Section, Enrollment, Assignment, Submission
from apps.ai.models import AcademicRiskPrediction, LearningRecommendation, PredictiveAlert
from apps.ai.ml_models import AcademicRiskPredictor

def create_test_data():
    print("Creando datos de prueba para el sistema de IA...")
    
    # Obtener o crear escuela
    school, created = School.objects.get_or_create(
        name="Test School for AI",
        defaults={'subdomain': 'test-ai', 'is_active': True}
    )
    print(f"Escuela: {school.name}")
    
    # Crear usuarios de prueba
    students = []
    for i in range(5):
        student, created = User.objects.get_or_create(
            username=f"student_ai_{i+1}",
            defaults={
                'email': f"student_ai_{i+1}@test.com",
                'first_name': f"Estudiante",
                'last_name': f"AI {i+1}",
                'role': 'STUDENT',
                'school': school,
                'is_active': True
            }
        )
        students.append(student)
        print(f"Estudiante creado: {student.first_name} {student.last_name}")
    
    # Crear profesor
    professor, created = User.objects.get_or_create(
        username="professor_ai_test",
        defaults={
            'email': "professor_ai@test.com",
            'first_name': "Profesor",
            'last_name': "AI Test",
            'role': 'PROFESSOR',
            'school': school,
            'is_active': True
        }
    )
    print(f"Profesor creado: {professor.first_name} {professor.last_name}")
    
    # Crear materia
    subject, created = Subject.objects.get_or_create(
        subject_name="Matemáticas Avanzadas",
        subject_code="MATH101",
        defaults={
            'school': school,
            'created_at': datetime.now()
        }
    )
    print(f"Materia creada: {subject.subject_name}")
    
    # Crear sección
    section, created = Section.objects.get_or_create(
        section_name="Sección A",
        subject=subject,
        professor=professor,
        defaults={
            'school': school,
            'start_date': datetime.now().date(),
            'end_date': (datetime.now() + timedelta(days=90)).date(),
            'max_students': 30
        }
    )
    print(f"Sección creada: {section.section_name}")
    
    # Crear inscripciones
    enrollments = []
    for student in students:
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            section=section,
            defaults={
                'school': school,
                'status': 'ENROLLED',
                'enrollment_date': datetime.now().date()
            }
        )
        enrollments.append(enrollment)
        print(f"Inscripción creada para {student.first_name}")
    
    # Crear tareas
    assignments = []
    for i in range(3):
        assignment, created = Assignment.objects.get_or_create(
            title=f"Tarea {i+1} - Álgebra",
            section=section,
            defaults={
                'school': school,
                'description': f"Tarea de práctica sobre álgebra lineal",
                'due_date': datetime.now() + timedelta(days=7*(i+1)),
                'total_points': 100.00,
                'created_by': professor
            }
        )
        assignments.append(assignment)
        print(f"Tarea creada: {assignment.title}")
    
    # Crear entregas con diferentes niveles de rendimiento
    for i, student in enumerate(students):
        for j, assignment in enumerate(assignments):
            # Simular diferentes niveles de rendimiento
            if i == 0:  # Estudiante de alto riesgo
                points = random.randint(40, 60)
                is_late = random.choice([True, False])
                status = 'GRADED'
            elif i == 1:  # Estudiante de riesgo medio
                points = random.randint(60, 75)
                is_late = random.choice([True, False])
                status = 'GRADED'
            else:  # Estudiantes de bajo riesgo
                points = random.randint(80, 95)
                is_late = False
                status = 'GRADED'
            
            submission, created = Submission.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={
                    'school': school,
                    'content': f"Respuesta del estudiante {student.first_name}",
                    'status': status,
                    'points_earned': points,
                    'submitted_at': datetime.now() - timedelta(days=random.randint(1, 14))
                }
            )
            print(f"Entrega creada para {student.first_name} - {assignment.title}: {points} puntos")
    
    # Crear predicciones de riesgo de muestra
    risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    for i, student in enumerate(students):
        risk_level = risk_levels[min(i, len(risk_levels)-1)]
        risk_score = (i + 1) * 0.2  # 0.2, 0.4, 0.6, 0.8, 1.0
        
        prediction, created = AcademicRiskPrediction.objects.get_or_create(
            student=student,
            defaults={
                'school': school,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'confidence': 0.85,
                'factors': {
                    'attendance_rate': max(0.5, 1.0 - risk_score),
                    'assignment_completion_rate': max(0.6, 1.0 - risk_score),
                    'average_grade': max(60, 100 - (risk_score * 40)),
                    'late_submissions_count': int(risk_score * 5),
                    'participation_score': max(0.5, 1.0 - risk_score),
                    'study_time_hours': max(2, 10 - (risk_score * 8)),
                    'previous_semester_gpa': max(2.0, 4.0 - (risk_score * 2)),
                    'current_semester_gpa': max(2.0, 4.0 - (risk_score * 2)),
                    'days_since_last_login': int(risk_score * 10)
                },
                'predicted_outcome': f"El estudiante tiene un riesgo {risk_level.lower()} de no completar el curso exitosamente",
                'attendance_rate': max(0.5, 1.0 - risk_score),
                'assignment_completion_rate': max(0.6, 1.0 - risk_score),
                'average_grade': max(60, 100 - (risk_score * 40)),
                'late_submissions_count': int(risk_score * 5),
                'participation_score': max(0.5, 1.0 - risk_score),
                'study_time_hours': max(2, 10 - (risk_score * 8)),
                'previous_semester_gpa': max(2.0, 4.0 - (risk_score * 2)),
                'current_semester_gpa': max(2.0, 4.0 - (risk_score * 2)),
                'days_since_last_login': int(risk_score * 10),
                'is_active': True
            }
        )
        print(f"Predicción de riesgo creada para {student.first_name}: {risk_level}")
    
    # Crear recomendaciones de muestra
    recommendation_types = ['STUDY_RESOURCE', 'PRACTICE_EXERCISE', 'PEER_COLLABORATION', 'TEACHER_CONSULTATION']
    for i, student in enumerate(students):
        for j in range(2):  # 2 recomendaciones por estudiante
            rec_type = recommendation_types[j % len(recommendation_types)]
            recommendation, created = LearningRecommendation.objects.get_or_create(
                student=student,
                title=f"Recomendación {j+1} para {student.first_name}",
                defaults={
                    'school': school,
                    'recommendation_type': rec_type,
                    'description': f"Recomendación personalizada para mejorar el rendimiento académico",
                    'expected_impact': 0.3,
                    'time_requirement': '30 minutos',
                    'difficulty_level': 'medium',
                    'resources': [
                        {
                            'type': 'video',
                            'url': 'https://example.com/video',
                            'title': 'Video tutorial'
                        }
                    ],
                    'is_completed': False
                }
            )
            print(f"Recomendación creada para {student.first_name}")
    
    # Crear alertas de muestra
    alert_types = ['ACADEMIC_RISK', 'ENGAGEMENT_DROP', 'PERFORMANCE_TREND']
    for i, student in enumerate(students[:3]):  # Solo para los primeros 3 estudiantes
        alert, created = PredictiveAlert.objects.get_or_create(
            student=student,
            alert_type=alert_types[i % len(alert_types)],
            defaults={
                'school': school,
                'priority': 'HIGH' if i == 0 else 'MEDIUM',
                'confidence_score': 0.8,
                'predicted_outcome': f"El estudiante {student.first_name} necesita intervención",
                'recommended_actions': [
                    "Contactar al estudiante",
                    "Revisar tareas pendientes",
                    "Programar tutoría"
                ],
                'supporting_evidence': {
                    'attendance_drop': '20%',
                    'grade_decline': '15%',
                    'late_submissions': '3'
                },
                'is_active': True
            }
        )
        print(f"Alerta creada para {student.first_name}")
    
    print("\n✅ Datos de prueba creados exitosamente!")
    print(f"📊 Resumen:")
    print(f"   - Estudiantes: {len(students)}")
    print(f"   - Profesor: 1")
    print(f"   - Materia: 1")
    print(f"   - Sección: 1")
    print(f"   - Tareas: {len(assignments)}")
    print(f"   - Predicciones de riesgo: {len(students)}")
    print(f"   - Recomendaciones: {len(students) * 2}")
    print(f"   - Alertas: 3")

if __name__ == '__main__':
    create_test_data() 