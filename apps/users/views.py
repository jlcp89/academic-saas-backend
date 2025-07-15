from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import check_password
from .models import User
from .serializers import UserSerializer, CreateUserSerializer, UpdateUserSerializer, ChangePasswordSerializer
from apps.base import TenantAwareViewSet
from apps.permissions import IsSchoolAdmin, IsSuperAdmin, IsOwnerOrAdmin

class UserViewSet(TenantAwareViewSet):
    """
    ViewSet for managing users within a school.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            permission_classes = [IsSchoolAdmin | IsSuperAdmin]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsOwnerOrAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateUserSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        return UserSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.SUPERADMIN:
            return User.objects.all()
        elif user.role == User.Role.ADMIN:
            return User.objects.filter(school=user.school)
        else:
            return User.objects.filter(id=user.id)
    
    def perform_create(self, serializer):
        """Ensure users are created with the correct school"""
        user = self.request.user
        if user.role == User.Role.ADMIN:
            serializer.save(school=user.school)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's information"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password"""
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            if not check_password(serializer.data.get('old_password'), user.password):
                return Response(
                    {'old_password': ['Wrong password.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(serializer.data.get('new_password'))
            user.save()
            return Response({'status': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def professors(self, request):
        """Get all professors in the school"""
        professors = self.get_queryset().filter(role=User.Role.PROFESSOR)
        serializer = self.get_serializer(professors, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def students(self, request):
        """Get all students in the school"""
        students = self.get_queryset().filter(role=User.Role.STUDENT)
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data)