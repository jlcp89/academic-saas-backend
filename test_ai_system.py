#!/usr/bin/env python
"""
Script para probar el sistema de predicción de riesgo académico
"""
import os
import sys
import django
import requests
import json
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User, School
from apps.ai.models import AcademicRiskPrediction, LearningRecommendation, PredictiveAlert

def test_backend_api():
    """Probar las APIs del backend"""
    print("🧪 PROBANDO APIS DEL BACKEND")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api"
    
    # Probar endpoint de predicciones de riesgo
    try:
        response = requests.get(f"{base_url}/ai/risk-predictions/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Predicciones de riesgo: {len(data)} encontradas")
            for pred in data[:3]:  # Mostrar las primeras 3
                print(f"   - {pred.get('student_name', 'N/A')}: {pred.get('risk_level', 'N/A')} ({pred.get('risk_score', 'N/A')})")
        else:
            print(f"❌ Error en predicciones de riesgo: {response.status_code}")
    except Exception as e:
        print(f"❌ Error conectando al backend: {e}")
    
    # Probar endpoint de recomendaciones
    try:
        response = requests.get(f"{base_url}/ai/learning-recommendations/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Recomendaciones: {len(data)} encontradas")
        else:
            print(f"❌ Error en recomendaciones: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en recomendaciones: {e}")
    
    # Probar endpoint de alertas
    try:
        response = requests.get(f"{base_url}/ai/predictive-alerts/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Alertas: {len(data)} encontradas")
        else:
            print(f"❌ Error en alertas: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en alertas: {e}")

def test_database_data():
    """Verificar datos en la base de datos"""
    print("\n🗄️ VERIFICANDO DATOS EN LA BASE DE DATOS")
    print("=" * 50)
    
    # Verificar predicciones
    predictions = AcademicRiskPrediction.objects.all()
    print(f"📊 Predicciones de riesgo: {predictions.count()}")
    
    for pred in predictions[:3]:
        print(f"   - {pred.student.first_name} {pred.student.last_name}: {pred.risk_level} (Score: {pred.risk_score})")
    
    # Verificar recomendaciones
    recommendations = LearningRecommendation.objects.all()
    print(f"📚 Recomendaciones: {recommendations.count()}")
    
    # Verificar alertas
    alerts = PredictiveAlert.objects.all()
    print(f"🚨 Alertas: {alerts.count()}")
    
    # Verificar estudiantes
    students = User.objects.filter(role='STUDENT')
    print(f"👥 Estudiantes: {students.count()}")
    
    # Verificar escuelas
    schools = School.objects.all()
    print(f"🏫 Escuelas: {schools.count()}")

def test_model_functionality():
    """Probar funcionalidad del modelo"""
    print("\n🤖 PROBANDO FUNCIONALIDAD DEL MODELO")
    print("=" * 50)
    
    from apps.ai.ml_models import AcademicRiskPredictor, DataCollector
    
    # Probar recolector de datos
    try:
        student = User.objects.filter(role='STUDENT').first()
        school = School.objects.first()
        
        if student and school:
            data = DataCollector.collect_student_data(student, school)
            if data:
                print(f"✅ Datos recolectados para {student.first_name}:")
                print(f"   - Asistencia: {data.get('attendance_rate', 'N/A')}")
                print(f"   - Completitud tareas: {data.get('assignment_completion_rate', 'N/A')}")
                print(f"   - Calificación promedio: {data.get('average_grade', 'N/A')}")
            else:
                print("❌ No se pudieron recolectar datos")
        else:
            print("❌ No se encontraron estudiantes o escuelas")
    except Exception as e:
        print(f"❌ Error en recolector de datos: {e}")
    
    # Probar predictor
    try:
        predictor = AcademicRiskPredictor()
        if predictor.model is not None:
            print("✅ Modelo de predicción cargado correctamente")
        else:
            print("⚠️ Modelo no entrenado, usando predicción por defecto")
    except Exception as e:
        print(f"❌ Error en predictor: {e}")

def test_frontend_access():
    """Probar acceso al frontend"""
    print("\n🌐 PROBANDO ACCESO AL FRONTEND")
    print("=" * 50)
    
    try:
        response = requests.get("http://localhost:3000")
        if response.status_code == 200:
            print("✅ Frontend accesible en http://localhost:3000")
        else:
            print(f"❌ Frontend no accesible: {response.status_code}")
    except Exception as e:
        print(f"❌ Error accediendo al frontend: {e}")

def main():
    """Función principal de pruebas"""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE PREDICCIÓN DE RIESGO ACADÉMICO")
    print("=" * 70)
    print(f"⏰ Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar todas las pruebas
    test_database_data()
    test_model_functionality()
    test_backend_api()
    test_frontend_access()
    
    print("\n" + "=" * 70)
    print("✅ PRUEBAS COMPLETADAS")
    print("\n📋 RESUMEN:")
    print("   - Backend: http://localhost:8000")
    print("   - Frontend: http://localhost:3000")
    print("   - API Docs: http://localhost:8000/api/")
    print("\n🎯 PRÓXIMOS PASOS:")
    print("   1. Abrir http://localhost:3000 en el navegador")
    print("   2. Iniciar sesión con un usuario estudiante")
    print("   3. Navegar a 'IA - Riesgo Académico' en el menú")
    print("   4. Verificar que se muestren las predicciones y recomendaciones")

if __name__ == '__main__':
    main() 