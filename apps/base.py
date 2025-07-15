from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class TenantAwareViewSet(viewsets.ModelViewSet):
    """
    A ViewSet that automatically filters querysets to objects
    belonging to the current user's school.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'school') and user.school is not None:
            return super().get_queryset().filter(school=user.school)
        return self.queryset.model.objects.none()
    
    def perform_create(self, serializer):
        """Automatically set the school when creating objects"""
        if hasattr(self.request.user, 'school') and self.request.user.school:
            serializer.save(school=self.request.user.school)
        else:
            serializer.save()