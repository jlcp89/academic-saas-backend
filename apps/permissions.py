from rest_framework import permissions
from apps.users.models import User

class IsSuperAdmin(permissions.BasePermission):
    """
    Allow access only to superadmin users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.SUPERADMIN

class IsSchoolAdmin(permissions.BasePermission):
    """
    Allow access only to school admin users of their own school.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.ADMIN

class IsProfessor(permissions.BasePermission):
    """
    Allow access only to professor users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.PROFESSOR

class IsStudent(permissions.BasePermission):
    """
    Allow access only to student users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.STUDENT

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins to access it.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role in [User.Role.SUPERADMIN, User.Role.ADMIN]:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'student'):
            return obj.student == request.user
        if hasattr(obj, 'professor'):
            return obj.professor == request.user
        return False

class IsSameSchool(permissions.BasePermission):
    """
    Ensure users can only access data from their own school.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.role == User.Role.SUPERADMIN:
            return True
        if hasattr(obj, 'school'):
            return obj.school == request.user.school
        return False