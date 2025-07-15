from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import School, Subscription
from .serializers import SchoolSerializer, SubscriptionSerializer, CreateSchoolSerializer
from apps.permissions import IsSuperAdmin

class SchoolViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing schools (tenants). Only accessible by superadmins.
    """
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [IsSuperAdmin]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSchoolSerializer
        return SchoolSerializer
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a school"""
        school = self.get_object()
        school.is_active = False
        school.save()
        return Response({'status': 'School deactivated'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a school"""
        school = self.get_object()
        school.is_active = True
        school.save()
        return Response({'status': 'School activated'})

class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing subscriptions. Only accessible by superadmins.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsSuperAdmin]
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get all expired subscriptions"""
        expired_subs = Subscription.objects.filter(
            end_date__lt=timezone.now().date(),
            status=Subscription.StatusChoices.ACTIVE
        )
        serializer = self.get_serializer(expired_subs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """Renew a subscription"""
        subscription = self.get_object()
        new_end_date = request.data.get('end_date')
        if not new_end_date:
            return Response(
                {'error': 'end_date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.end_date = new_end_date
        subscription.status = Subscription.StatusChoices.ACTIVE
        subscription.save()
        return Response(self.get_serializer(subscription).data)