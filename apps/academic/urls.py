from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubjectViewSet, SectionViewSet, EnrollmentViewSet, AssignmentViewSet, SubmissionViewSet

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'assignments', AssignmentViewSet)
router.register(r'submissions', SubmissionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]