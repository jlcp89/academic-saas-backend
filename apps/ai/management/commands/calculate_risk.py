from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
from apps.organizations.models import School
from apps.ai.tasks import calculate_student_risk, update_all_risk_predictions
from apps.ai.models import AcademicRiskPrediction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Calculate academic risk for students'

    def add_arguments(self, parser):
        parser.add_argument(
            '--school-id',
            type=int,
            help='Calculate risk for specific school (optional)',
        )
        parser.add_argument(
            '--student-id',
            type=int,
            help='Calculate risk for specific student (optional)',
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update existing risk predictions',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run calculations asynchronously using Celery',
        )

    def handle(self, *args, **options):
        school_id = options.get('school_id')
        student_id = options.get('student_id')
        force_update = options.get('force_update')
        async_mode = options.get('async')

        self.stdout.write(
            self.style.SUCCESS('Starting academic risk calculation...')
        )

        try:
            if student_id:
                # Calcular riesgo para un estudiante específico
                self.calculate_single_student_risk(student_id, async_mode)
            elif school_id:
                # Calcular riesgo para una escuela específica
                self.calculate_school_risk(school_id, force_update, async_mode)
            else:
                # Calcular riesgo para todas las escuelas
                self.calculate_all_schools_risk(force_update, async_mode)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during risk calculation: {e}')
            )
            logger.error(f'Error in calculate_risk command: {e}')

    def calculate_single_student_risk(self, student_id, async_mode):
        """
        Calcular riesgo para un estudiante específico
        """
        try:
            student = User.objects.get(id=student_id, role='STUDENT')
            
            self.stdout.write(
                f'Calculating risk for student: {student.username} ({student.email})'
            )

            if async_mode:
                # Ejecutar de forma asíncrona
                task = calculate_student_risk.delay(student_id)
                self.stdout.write(
                    self.style.SUCCESS(f'Risk calculation task queued: {task.id}')
                )
            else:
                # Ejecutar de forma síncrona
                from apps.ai.ml_models import AcademicRiskPredictor, DataCollector
                
                student_data = DataCollector.collect_student_data(student, student.school)
                if student_data:
                    predictor = AcademicRiskPredictor()
                    prediction = predictor.predict_risk(student_data)
                    
                    # Guardar predicción
                    risk_prediction, created = AcademicRiskPrediction.objects.update_or_create(
                        school=student.school,
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
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Risk calculation completed for {student.username}:\n'
                            f'  Risk Level: {prediction["risk_level"]}\n'
                            f'  Risk Score: {prediction["risk_score"]:.3f}\n'
                            f'  Confidence: {prediction["confidence"]:.3f}\n'
                            f'  Status: {"Created" if created else "Updated"}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'No data available for student {student.username}')
                    )

        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Student with ID {student_id} not found')
            )

    def calculate_school_risk(self, school_id, force_update, async_mode):
        """
        Calcular riesgo para una escuela específica
        """
        try:
            school = School.objects.get(id=school_id)
            
            self.stdout.write(
                f'Calculating risk for school: {school.name}'
            )

            students = User.objects.filter(
                role='STUDENT',
                school=school
            )

            if not students.exists():
                self.stdout.write(
                    self.style.WARNING(f'No students found in school {school.name}')
                )
                return

            total_students = students.count()
            self.stdout.write(f'Found {total_students} students')

            if async_mode:
                # Ejecutar de forma asíncrona
                task = update_all_risk_predictions.delay()
                self.stdout.write(
                    self.style.SUCCESS(f'Bulk risk calculation task queued: {task.id}')
                )
            else:
                # Ejecutar de forma síncrona
                updated_count = 0
                for student in students:
                    try:
                        # Verificar si ya existe predicción y no forzar actualización
                        if not force_update:
                            existing_prediction = AcademicRiskPrediction.objects.filter(
                                student=student,
                                is_active=True
                            ).first()
                            
                            if existing_prediction:
                                self.stdout.write(
                                    f'Skipping {student.username} - prediction already exists'
                                )
                                continue

                        # Calcular riesgo
                        from apps.ai.ml_models import AcademicRiskPredictor, DataCollector
                        
                        student_data = DataCollector.collect_student_data(student, school)
                        if student_data:
                            predictor = AcademicRiskPredictor()
                            prediction = predictor.predict_risk(student_data)
                            
                            # Guardar predicción
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
                            
                            updated_count += 1
                            self.stdout.write(
                                f'  {student.username}: {prediction["risk_level"]} (Score: {prediction["risk_score"]:.3f})'
                            )
                        else:
                            self.stdout.write(
                                f'  {student.username}: No data available'
                            )
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  Error calculating risk for {student.username}: {e}')
                        )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Risk calculation completed for {school.name}:\n'
                        f'  Total students: {total_students}\n'
                        f'  Updated: {updated_count}'
                    )
                )

        except School.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'School with ID {school_id} not found')
            )

    def calculate_all_schools_risk(self, force_update, async_mode):
        """
        Calcular riesgo para todas las escuelas
        """
        schools = School.objects.all()
        
        if not schools.exists():
            self.stdout.write(
                self.style.WARNING('No schools found in the system')
            )
            return

        self.stdout.write(f'Found {schools.count()} schools')

        if async_mode:
            # Ejecutar de forma asíncrona
            task = update_all_risk_predictions.delay()
            self.stdout.write(
                self.style.SUCCESS(f'Bulk risk calculation task queued: {task.id}')
            )
        else:
            # Ejecutar de forma síncrona para cada escuela
            for school in schools:
                self.stdout.write(f'\nProcessing school: {school.name}')
                self.calculate_school_risk(school.id, force_update, False)

        self.stdout.write(
            self.style.SUCCESS('Risk calculation process completed!')
        ) 