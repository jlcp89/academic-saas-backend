from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.db.models import Q, Count, Max, Prefetch, Subquery, Exists, OuterRef, F
from django.db import models
from django.shortcuts import get_object_or_404
from apps.base import TenantAwareViewSet
from .models import ChatRoom, Message, MessageRead
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomDetailSerializer,
    CreateChatRoomSerializer,
    MessageSerializer,
    MessageReadSerializer
)


class ChatRoomViewSet(TenantAwareViewSet):
    """ViewSet for chat room operations"""
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get chat rooms for current user with optimizations"""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Filter rooms where user is participant
        queryset = queryset.filter(
            participants=user,
            is_active=True
        )
        
        # Add annotations for list view
        if self.action == 'list':
            # Simple annotation for participant count
            queryset = queryset.annotate(
                participant_count=Count('participants')
            )
            
            # We'll calculate unread count in serializer for simplicity
            # This avoids complex subqueries
        
        return queryset.select_related('created_by').prefetch_related('participants')
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return ChatRoomListSerializer
        elif self.action == 'create':
            return CreateChatRoomSerializer
        return ChatRoomDetailSerializer
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get paginated messages for a chat room with caching"""
        room = self.get_object()
        page = request.GET.get('page', 1)
        
        # Cache key includes user to ensure proper isolation
        cache_key = f"room_{pk}_messages_page_{page}_user_{request.user.id}"
        
        # Try cache first (5 minute cache)
        cached_data = cache.get(cache_key)
        if cached_data and not request.GET.get('force_refresh'):
            return Response(cached_data)
        
        # Get messages with sender info
        messages = room.messages.select_related('sender').order_by('-created_at')
        
        # Paginate
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
            
            # Cache the response
            cache.set(cache_key, response_data, 300)  # 5 minutes
            
            # Update read status
            self._update_read_status(room, request.user)
            
            return Response(response_data)
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a text message to the chat room"""
        room = self.get_object()
        
        # Validate user is participant
        if not room.participants.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are not a participant in this chat room"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create message
        serializer = MessageSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save(room=room)
            
            # Clear cache for this room (delete_pattern only works with Redis)
            try:
                cache.delete_pattern(f"room_{pk}_messages_*")
            except AttributeError:
                # Fallback for development with LocMemCache
                # In production with Redis, delete_pattern will work
                pass
            
            # Trigger async notification (will implement with Celery)
            self._send_message_notification(room, message)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark messages as read up to a specific message"""
        room = self.get_object()
        message_id = request.data.get('last_read_message_id')
        
        if message_id:
            message = get_object_or_404(Message, id=message_id, room=room)
        else:
            # Mark all as read
            message = room.messages.last()
        
        if message:
            MessageRead.objects.update_or_create(
                user=request.user,
                room=room,
                defaults={'last_read_message': message}
            )
        
        return Response({"status": "marked as read"})
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get list of participants in the chat room"""
        room = self.get_object()
        from apps.users.serializers import UserSerializer
        
        participants = room.participants.all()
        serializer = UserSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to the chat room"""
        room = self.get_object()
        user_id = request.data.get('user_id')
        
        # Only room creator or admin can add participants
        if room.created_by != request.user and request.user.role not in ['ADMIN', 'SUPERADMIN']:
            return Response(
                {"error": "Only room creator or admin can add participants"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id, school=request.user.school)
            room.add_participant(user)
            
            # Send system message
            Message.objects.create(
                room=room,
                sender=request.user,
                content=f"{user.username} was added to the chat",
                is_system_message=True
            )
            
            return Response({"status": "participant added"})
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _update_read_status(self, room, user):
        """Update read status for user in room"""
        last_message = room.messages.last()
        if last_message:
            MessageRead.objects.update_or_create(
                user=user,
                room=room,
                defaults={'last_read_message': last_message}
            )
    
    def _send_message_notification(self, room, message):
        """Send notification about new message via Celery"""
        from .tasks import send_message_notification
        # Send async notification
        send_message_notification.delay(room.id, message.id)
