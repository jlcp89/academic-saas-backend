from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'risk-predictions', views.AcademicRiskViewSet, basename='risk-prediction')
router.register(r'risk-dashboard', views.RiskDashboardViewSet, basename='risk-dashboard')

urlpatterns = [
    # Rutas del router
    path('', include(router.urls)),
    
    # Rutas específicas para dashboards
    path('student-risk-dashboard/', views.student_risk_dashboard, name='student-risk-dashboard'),
    path('recommendations/<int:recommendation_id>/complete/', views.mark_recommendation_completed, name='mark-recommendation-completed'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge-alert'),
    
    # Rutas para dashboards específicos
    path('dashboard/class/<int:section_id>/', views.RiskDashboardViewSet.as_view({'get': 'class_overview'}), name='class-risk-overview'),
    path('dashboard/student/<int:student_id>/', views.RiskDashboardViewSet.as_view({'get': 'student_summary'}), name='student-risk-summary'),
] 