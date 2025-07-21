from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.ai.ml_models import AcademicRiskPredictor, DataCollector
from apps.users.models import User
from apps.organizations.models import School
from apps.ai.models import AITrainingSession
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Train the academic risk prediction model with historical data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--school-id',
            type=int,
            help='Train model for specific school (optional)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retraining even if model exists',
        )
        parser.add_argument(
            '--generate-sample-data',
            action='store_true',
            help='Generate sample training data if no real data exists',
        )

    def handle(self, *args, **options):
        school_id = options.get('school_id')
        force = options.get('force')
        generate_sample = options.get('generate_sample_data')

        self.stdout.write(
            self.style.SUCCESS('Starting academic risk model training...')
        )

        try:
            # Determinar escuelas para entrenar
            if school_id:
                schools = School.objects.filter(id=school_id)
                if not schools.exists():
                    self.stdout.write(
                        self.style.ERROR(f'School with ID {school_id} not found')
                    )
                    return
            else:
                schools = School.objects.all()

            for school in schools:
                self.stdout.write(
                    self.style.SUCCESS(f'Training model for school: {school.name}')
                )

                # Recopilar datos de entrenamiento
                training_data = self.collect_training_data(school)

                if training_data.empty and generate_sample:
                    self.stdout.write(
                        self.style.WARNING('No real data found, generating sample data...')
                    )
                    training_data = self.generate_sample_data(school)

                if training_data.empty:
                    self.stdout.write(
                        self.style.ERROR(f'No training data available for school {school.name}')
                    )
                    continue

                # Entrenar modelo
                predictor = AcademicRiskPredictor()
                
                # Verificar si ya existe un modelo entrenado
                if predictor.is_trained and not force:
                    self.stdout.write(
                        self.style.WARNING('Model already trained. Use --force to retrain.')
                    )
                    continue

                # Entrenar modelo
                training_result = predictor.train_model(training_data)

                if training_result:
                    # Guardar sesión de entrenamiento
                    session = AITrainingSession.objects.create(
                        school=school,
                        session_name=f'Risk Model Training - {timezone.now().strftime("%Y-%m-%d %H:%M")}',
                        model_type='academic_risk_prediction',
                        training_data_size=len(training_data),
                        validation_accuracy=training_result['accuracy'],
                        model_parameters={
                            'n_estimators': 100,
                            'max_depth': 10,
                            'random_state': 42
                        },
                        feature_importance=training_result['feature_importance'],
                        is_active=True,
                        deployment_date=timezone.now()
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Model trained successfully for {school.name}!\n'
                            f'Accuracy: {training_result["accuracy"]:.3f}\n'
                            f'Training data size: {len(training_data)}\n'
                            f'Session ID: {session.id}'
                        )
                    )

                    # Mostrar importancia de características
                    self.stdout.write('\nFeature Importance:')
                    for feature, importance in sorted(
                        training_result['feature_importance'].items(),
                        key=lambda x: x[1],
                        reverse=True
                    ):
                        self.stdout.write(f'  {feature}: {importance:.3f}')

                else:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to train model for {school.name}')
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during training: {e}')
            )
            logger.error(f'Error in train_risk_model command: {e}')

    def collect_training_data(self, school):
        """
        Recopilar datos reales de entrenamiento
        """
        students = User.objects.filter(
            role='STUDENT',
            school=school
        )

        training_data = []
        
        for student in students:
            student_data = DataCollector.collect_student_data(student, school)
            if student_data:
                # Determinar si el estudiante está en riesgo (simulado)
                # En un caso real, esto se basaría en datos históricos
                is_at_risk = self.determine_risk_label(student_data)
                
                training_row = {
                    'student_id': student.id,
                    'is_at_risk': is_at_risk,
                    **student_data
                }
                training_data.append(training_row)

        return pd.DataFrame(training_data)

    def determine_risk_label(self, student_data):
        """
        Determinar etiqueta de riesgo basada en datos del estudiante
        """
        # Lógica simple para determinar riesgo
        risk_score = 0
        
        if student_data.get('attendance_rate', 1) < 0.8:
            risk_score += 1
        
        if student_data.get('assignment_completion_rate', 1) < 0.7:
            risk_score += 1
        
        if student_data.get('average_grade', 100) < 70:
            risk_score += 1
        
        if student_data.get('days_since_last_login', 0) > 7:
            risk_score += 1
        
        # Considerar en riesgo si tiene 2 o más factores problemáticos
        return risk_score >= 2

    def generate_sample_data(self, school):
        """
        Generar datos de muestra para entrenamiento
        """
        np.random.seed(42)
        n_samples = 1000
        
        # Generar datos sintéticos
        data = {
            'student_id': range(1, n_samples + 1),
            'attendance_rate': np.random.beta(2, 1, n_samples),  # Sesgado hacia valores altos
            'assignment_completion_rate': np.random.beta(2, 1, n_samples),
            'average_grade': np.random.normal(75, 15, n_samples),  # Media 75, std 15
            'late_submissions_rate': np.random.beta(1, 3, n_samples),  # Sesgado hacia valores bajos
            'participation_score': np.random.beta(2, 1, n_samples),
            'study_time_hours': np.random.exponential(2, n_samples),  # Media 2 horas
            'previous_semester_gpa': np.random.normal(3.0, 0.5, n_samples),
            'current_semester_gpa': np.random.normal(3.0, 0.5, n_samples),
            'days_since_last_login': np.random.exponential(3, n_samples),
            'failed_assignments_rate': np.random.beta(1, 4, n_samples),
            'submission_delay_hours': np.random.exponential(12, n_samples),
            'login_frequency': np.random.beta(2, 1, n_samples)
        }
        
        # Asegurar que los valores estén en rangos razonables
        data['attendance_rate'] = np.clip(data['attendance_rate'], 0, 1)
        data['assignment_completion_rate'] = np.clip(data['assignment_completion_rate'], 0, 1)
        data['average_grade'] = np.clip(data['average_grade'], 0, 100)
        data['late_submissions_rate'] = np.clip(data['late_submissions_rate'], 0, 1)
        data['participation_score'] = np.clip(data['participation_score'], 0, 1)
        data['study_time_hours'] = np.clip(data['study_time_hours'], 0, 24)
        data['previous_semester_gpa'] = np.clip(data['previous_semester_gpa'], 0, 4)
        data['current_semester_gpa'] = np.clip(data['current_semester_gpa'], 0, 4)
        data['days_since_last_login'] = np.clip(data['days_since_last_login'], 0, 365)
        data['failed_assignments_rate'] = np.clip(data['failed_assignments_rate'], 0, 1)
        data['submission_delay_hours'] = np.clip(data['submission_delay_hours'], 0, 168)  # 1 semana
        data['login_frequency'] = np.clip(data['login_frequency'], 0, 1)
        
        # Generar etiquetas de riesgo basadas en los datos
        risk_labels = []
        for i in range(n_samples):
            risk_score = 0
            
            if data['attendance_rate'][i] < 0.8:
                risk_score += 1
            if data['assignment_completion_rate'][i] < 0.7:
                risk_score += 1
            if data['average_grade'][i] < 70:
                risk_score += 1
            if data['days_since_last_login'][i] > 7:
                risk_score += 1
            if data['late_submissions_rate'][i] > 0.3:
                risk_score += 1
            if data['participation_score'][i] < 0.6:
                risk_score += 1
            
            risk_labels.append(risk_score >= 2)
        
        data['is_at_risk'] = risk_labels
        
        return pd.DataFrame(data) 