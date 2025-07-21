import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class AcademicRiskPredictor:
    """
    Modelo de machine learning para predecir riesgo académico
    """
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Características del modelo
        self.feature_names = [
            'attendance_rate',
            'assignment_completion_rate', 
            'average_grade',
            'late_submissions_rate',
            'participation_score',
            'study_time_hours',
            'previous_semester_gpa',
            'current_semester_gpa',
            'days_since_last_login',
            'failed_assignments_rate',
            'submission_delay_hours',
            'login_frequency'
        ]
        
        # Cargar modelo si existe
        self.load_model()
    
    def prepare_features(self, student_data):
        """
        Preparar características del estudiante para predicción
        """
        features = []
        for feature in self.feature_names:
            value = student_data.get(feature, 0)
            # Normalizar valores
            if feature in ['attendance_rate', 'assignment_completion_rate', 'participation_score']:
                value = min(max(value, 0), 1)  # Clamp entre 0 y 1
            elif feature in ['average_grade', 'previous_semester_gpa', 'current_semester_gpa']:
                value = min(max(value, 0), 100) / 100  # Normalizar a 0-1
            elif feature == 'days_since_last_login':
                value = min(value, 365) / 365  # Normalizar a 0-1
            elif feature == 'study_time_hours':
                value = min(value, 24) / 24  # Normalizar a 0-1
            
            features.append(float(value))
        
        return np.array(features).reshape(1, -1)
    
    def predict_risk(self, student_data):
        """
        Predecir riesgo académico para un estudiante
        """
        try:
            if not self.is_trained:
                logger.warning("Model not trained, using default prediction")
                return self._default_prediction(student_data)
            
            features = self.prepare_features(student_data)
            features_scaled = self.scaler.transform(features)
            
            # Predecir probabilidad de riesgo
            risk_probability = self.model.predict_proba(features_scaled)[0][1]
            
            # Determinar nivel de riesgo
            risk_level = self._determine_risk_level(risk_probability)
            
            # Calcular confianza basada en la distribución de probabilidades
            confidence = self._calculate_confidence(features_scaled)
            
            # Identificar factores de riesgo
            factors = self._identify_risk_factors(student_data, features[0])
            
            # Generar predicción de resultado
            predicted_outcome = self._generate_outcome_prediction(risk_level, factors)
            
            return {
                'risk_score': float(risk_probability),
                'risk_level': risk_level,
                'confidence': float(confidence),
                'factors': factors,
                'predicted_outcome': predicted_outcome
            }
            
        except Exception as e:
            logger.error(f"Error in risk prediction: {e}")
            return self._default_prediction(student_data)
    
    def _determine_risk_level(self, risk_probability):
        """
        Determinar nivel de riesgo basado en probabilidad
        """
        if risk_probability < 0.25:
            return 'LOW'
        elif risk_probability < 0.5:
            return 'MEDIUM'
        elif risk_probability < 0.75:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def _calculate_confidence(self, features_scaled):
        """
        Calcular nivel de confianza de la predicción
        """
        # Basado en la distancia a los datos de entrenamiento
        # Por ahora, retornamos un valor fijo
        return 0.85
    
    def _identify_risk_factors(self, student_data, features):
        """
        Identificar factores principales de riesgo
        """
        factors = {}
        
        # Mapear características a factores legibles
        factor_mapping = {
            'attendance_rate': 'Asistencia baja',
            'assignment_completion_rate': 'Tareas incompletas',
            'average_grade': 'Calificaciones bajas',
            'late_submissions_rate': 'Entregas tardías',
            'participation_score': 'Baja participación',
            'study_time_hours': 'Poco tiempo de estudio',
            'previous_semester_gpa': 'GPA anterior bajo',
            'current_semester_gpa': 'GPA actual bajo',
            'days_since_last_login': 'Inactividad reciente',
            'failed_assignments_rate': 'Tareas fallidas',
            'submission_delay_hours': 'Retrasos en entregas',
            'login_frequency': 'Baja frecuencia de acceso'
        }
        
        # Identificar factores problemáticos
        for i, feature in enumerate(self.feature_names):
            if feature in factor_mapping:
                feature_value = features[i]
                if feature_value > 0.7:  # Factor de alto riesgo
                    factors[factor_mapping[feature]] = {
                        'severity': 'HIGH',
                        'value': feature_value,
                        'description': f"Factor crítico: {factor_mapping[feature]}"
                    }
                elif feature_value > 0.5:  # Factor de riesgo medio
                    factors[factor_mapping[feature]] = {
                        'severity': 'MEDIUM',
                        'value': feature_value,
                        'description': f"Factor de riesgo: {factor_mapping[feature]}"
                    }
        
        return factors
    
    def _generate_outcome_prediction(self, risk_level, factors):
        """
        Generar predicción de resultado basada en nivel de riesgo y factores
        """
        if risk_level == 'LOW':
            return "El estudiante muestra buenos indicadores académicos y se espera que mantenga un rendimiento satisfactorio."
        elif risk_level == 'MEDIUM':
            return "El estudiante presenta algunos factores de riesgo que requieren atención. Con intervención temprana, puede mejorar su rendimiento."
        elif risk_level == 'HIGH':
            return "El estudiante presenta múltiples factores de riesgo significativos. Se requiere intervención inmediata para evitar problemas académicos."
        else:  # CRITICAL
            return "El estudiante presenta un riesgo crítico de fracaso académico. Se requiere intervención urgente y seguimiento intensivo."
    
    def _default_prediction(self, student_data):
        """
        Predicción por defecto cuando el modelo no está entrenado
        """
        # Análisis básico basado en reglas simples
        risk_score = 0.0
        factors = {}
        
        if student_data.get('attendance_rate', 1) < 0.8:
            risk_score += 0.2
            factors['Asistencia baja'] = {'severity': 'MEDIUM', 'value': 0.8 - student_data.get('attendance_rate', 1)}
        
        if student_data.get('assignment_completion_rate', 1) < 0.7:
            risk_score += 0.3
            factors['Tareas incompletas'] = {'severity': 'HIGH', 'value': 0.7 - student_data.get('assignment_completion_rate', 1)}
        
        if student_data.get('average_grade', 100) < 70:
            risk_score += 0.4
            factors['Calificaciones bajas'] = {'severity': 'HIGH', 'value': (70 - student_data.get('average_grade', 100)) / 100}
        
        risk_level = self._determine_risk_level(risk_score)
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'confidence': 0.6,
            'factors': factors,
            'predicted_outcome': self._generate_outcome_prediction(risk_level, factors)
        }
    
    def train_model(self, training_data):
        """
        Entrenar modelo con datos históricos
        """
        try:
            # Preparar datos de entrenamiento
            X = training_data[self.feature_names]
            y = training_data['is_at_risk']
            
            # Dividir datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Escalar características
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Entrenar modelo
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluar modelo
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Guardar modelo
            self.save_model()
            self.is_trained = True
            
            logger.info(f"Model trained successfully with accuracy: {accuracy:.3f}")
            
            return {
                'accuracy': accuracy,
                'classification_report': classification_report(y_test, y_pred),
                'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_))
            }
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return None
    
    def save_model(self):
        """
        Guardar modelo entrenado
        """
        try:
            model_dir = os.path.join(settings.BASE_DIR, 'models')
            os.makedirs(model_dir, exist_ok=True)
            
            model_path = os.path.join(model_dir, 'academic_risk_model.pkl')
            scaler_path = os.path.join(model_dir, 'academic_risk_scaler.pkl')
            
            joblib.dump(self.model, model_path)
            joblib.dump(self.scaler, scaler_path)
            
            logger.info("Model saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self):
        """
        Cargar modelo entrenado
        """
        try:
            model_dir = os.path.join(settings.BASE_DIR, 'models')
            model_path = os.path.join(model_dir, 'academic_risk_model.pkl')
            scaler_path = os.path.join(model_dir, 'academic_risk_scaler.pkl')
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.is_trained = True
                logger.info("Model loaded successfully")
            else:
                logger.info("No trained model found, will use default predictions")
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.is_trained = False

class DataCollector:
    """
    Clase para recopilar datos de estudiantes para el modelo
    """
    
    @staticmethod
    def collect_student_data(student, school):
        """
        Recopilar datos de un estudiante para análisis de riesgo
        """
        from apps.academic.models import Assignment, Submission, Enrollment
        from django.db.models import Avg, Count, Q
        from django.utils import timezone
        
        now = timezone.now()
        semester_start = now - timedelta(days=90)  # Últimos 3 meses
        
        try:
            # Enrollments activos
            enrollments = Enrollment.objects.filter(
                student=student,
                school=school,
                status='ENROLLED'
            )
            
            if not enrollments.exists():
                return None
            
            # Assignments y submissions
            assignments = Assignment.objects.filter(
                section__enrollments__student=student,
                section__school=school
            )
            
            submissions = Submission.objects.filter(
                assignment__in=assignments,
                student=student
            )
            
            # Calcular métricas básicas
            total_assignments = assignments.count()
            completed_assignments = submissions.filter(status='SUBMITTED').count()
            from django.db.models import F
            
            late_submissions = submissions.filter(
                submitted_at__gt=F('assignment__due_date')
            ).count()
            
            failed_assignments = submissions.filter(
                points_earned__lt=F('assignment__total_points') * 0.6
            ).count()
            
            # Calificaciones
            grades = submissions.filter(
                points_earned__isnull=False
            ).values_list('points_earned', flat=True)
            
            average_grade = sum(grades) / len(grades) if grades else 0
            
            # Asistencia (simulada por ahora)
            attendance_rate = 0.85  # Placeholder
            
            # Participación (simulada)
            participation_score = 0.75  # Placeholder
            
            # Tiempo de estudio (simulado)
            study_time_hours = 2.5  # Placeholder
            
            # GPA anterior y actual (simulado)
            previous_semester_gpa = 3.2  # Placeholder
            current_semester_gpa = 3.0  # Placeholder
            
            # Días desde último login
            days_since_last_login = (now - student.last_login).days if student.last_login else 999
            
            # Frecuencia de login (simulada)
            login_frequency = 0.8  # Placeholder
            
            # Calcular tasas
            assignment_completion_rate = completed_assignments / total_assignments if total_assignments > 0 else 0
            late_submissions_rate = late_submissions / total_assignments if total_assignments > 0 else 0
            failed_assignments_rate = failed_assignments / total_assignments if total_assignments > 0 else 0
            
            # Retraso promedio en entregas (simulado)
            submission_delay_hours = 24  # Placeholder
            
            return {
                'attendance_rate': attendance_rate,
                'assignment_completion_rate': assignment_completion_rate,
                'average_grade': average_grade,
                'late_submissions_rate': late_submissions_rate,
                'participation_score': participation_score,
                'study_time_hours': study_time_hours,
                'previous_semester_gpa': previous_semester_gpa,
                'current_semester_gpa': current_semester_gpa,
                'days_since_last_login': days_since_last_login,
                'failed_assignments_rate': failed_assignments_rate,
                'submission_delay_hours': submission_delay_hours,
                'login_frequency': login_frequency
            }
            
        except Exception as e:
            logger.error(f"Error collecting data for student {student.id}: {e}")
            return None 