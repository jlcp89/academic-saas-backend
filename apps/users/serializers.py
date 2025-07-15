from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User
from apps.organizations.serializers import SchoolSerializer

class UserSerializer(serializers.ModelSerializer):
    school_info = SchoolSerializer(source='school', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'school', 'school_info', 'is_active', 'date_joined']
        read_only_fields = ['date_joined']
        extra_kwargs = {'school': {'write_only': True}}

class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'school']
    
    def validate_password(self, value):
        return make_password(value)
    
    def validate(self, attrs):
        if attrs.get('role') != User.Role.SUPERADMIN and not attrs.get('school'):
            raise serializers.ValidationError("School is required for non-superadmin users")
        return attrs

class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'is_active']

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)