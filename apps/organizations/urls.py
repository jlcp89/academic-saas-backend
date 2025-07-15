from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SchoolViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register(r'schools', SchoolViewSet)
router.register(r'subscriptions', SubscriptionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]