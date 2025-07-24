from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
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


class MessagePagination(PageNumberPagination):
    """Custom pagination for messages - returns 100 messages per page"""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500


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
    
    @action(detail=True, methods=['get'], pagination_class=MessagePagination)
    def messages(self, request, pk=None):
        """Get paginated messages for a chat room with caching"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 [CHAT DEBUG] Messages request - Room: {pk}, User: {request.user.id}, Page: {request.GET.get('page', 1)}")
        
        room = self.get_object()
        page = request.GET.get('page', 1)
        
        # Cache key includes user to ensure proper isolation
        cache_key = f"room_{pk}_messages_page_{page}_user_{request.user.id}"
        logger.info(f"🗂️ [CHAT DEBUG] Cache key: {cache_key}")
        
        # Try cache first (30 second cache instead of 5 minutes)
        # Skip cache if it's been less than 2 seconds since last message (to avoid stale cache issues)
        skip_cache = False
        last_message = room.messages.last()
        if last_message and last_message.created_at:
            from django.utils import timezone
            time_since_last = timezone.now() - last_message.created_at
            if time_since_last.total_seconds() < 2:
                skip_cache = True
                logger.info(f"⏰ [CHAT DEBUG] Skipping cache - last message was {time_since_last.total_seconds():.1f}s ago")
        
        cached_data = cache.get(cache_key)
        if cached_data and not request.GET.get('force_refresh') and not skip_cache:
            logger.info(f"💾 [CHAT DEBUG] Returning cached data for room {pk}")
            return Response(cached_data)
        
        logger.info(f"🔄 [CHAT DEBUG] Fetching fresh messages from database for room {pk}")
        
        # Get messages with sender info - chronological order for chat UI
        messages = room.messages.select_related('sender').order_by('created_at')
        message_count = messages.count()
        logger.info(f"📨 [CHAT DEBUG] Found {message_count} messages in room {pk}")
        
        # Use custom pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(messages, request)
        if page is not None:
            logger.info(f"📄 [CHAT DEBUG] Paginating {len(page)} messages")
            serializer = MessageSerializer(page, many=True)
            response_data = paginator.get_paginated_response(serializer.data).data
            
            # Cache the response for 30 seconds instead of 5 minutes
            cache.set(cache_key, response_data, 30)  # 30 seconds
            logger.info(f"💾 [CHAT DEBUG] Cached response for room {pk}")
            
            # Update read status
            self._update_read_status(room, request.user)
            
            logger.info(f"✅ [CHAT DEBUG] Returning paginated response with {len(serializer.data)} messages")
            return Response(response_data)
        
        logger.info(f"📄 [CHAT DEBUG] No pagination, returning all {message_count} messages")
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a text message to the chat room"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🚀 [CHAT DEBUG] Message send request - Room: {pk}, User: {request.user.id}, Data: {request.data}")
        
        room = self.get_object()
        logger.info(f"📍 [CHAT DEBUG] Room found: {room.id} - {room.name}")
        
        # Validate user is participant
        is_participant = room.participants.filter(id=request.user.id).exists()
        logger.info(f"👤 [CHAT DEBUG] User {request.user.id} is participant: {is_participant}")
        
        if not is_participant:
            logger.warning(f"❌ [CHAT DEBUG] User {request.user.id} not participant in room {room.id}")
            return Response(
                {"error": "You are not a participant in this chat room"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create message
        logger.info(f"🔄 [CHAT DEBUG] Creating message with data: {request.data}")
        serializer = MessageSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            logger.info(f"✅ [CHAT DEBUG] Serializer valid, saving message...")
            message = serializer.save(room=room)
            logger.info(f"💾 [CHAT DEBUG] Message saved - ID: {message.id}, Content: {message.content[:50]}...")
            
            # Clear cache for this room
            # Since delete_pattern might not be available, we'll clear specific cache keys
            try:
                # Clear first 10 pages of cache (should be enough for most cases)
                for page in range(1, 11):
                    for user_id in room.participants.values_list('id', flat=True):
                        cache_key = f"room_{pk}_messages_page_{page}_user_{user_id}"
                        cache.delete(cache_key)
                        logger.info(f"🗑️ [CHAT DEBUG] Cleared cache key: {cache_key}")
                
                # Also try delete_pattern if available (for Redis)
                if hasattr(cache, 'delete_pattern'):
                    cache.delete_pattern(f"room_{pk}_messages_*")
                    logger.info(f"🗑️ [CHAT DEBUG] Cache pattern cleared for room {pk}")
            except Exception as e:
                logger.warning(f"⚠️ [CHAT DEBUG] Cache clear error: {e}")
                pass
            
            # Send message via WebSocket to all participants
            logger.info(f"📡 [CHAT DEBUG] Sending message via WebSocket to room {pk}")
            self._send_message_via_websocket(room, message)
            
            response_data = serializer.data
            logger.info(f"✅ [CHAT DEBUG] Returning successful response: {response_data}")
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"❌ [CHAT DEBUG] Serializer errors: {serializer.errors}")
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
    
    def _send_message_via_websocket(self, room, message):
        """Send message to all participants via WebSocket"""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        import json
        
        channel_layer = get_channel_layer()
        room_group_name = f'chat_room_{room.id}'
        
        # Prepare message data for WebSocket
        message_data = {
            'id': message.id,
            'content': message.content,
            'sender': message.sender.id,
            'sender_name': message.sender.username,
            'sender_role': message.sender.role,
            'created_at': message.created_at.isoformat(),
            'is_edited': message.is_edited,
            'is_system_message': message.is_system_message,
            'room': room.id
        }
        
        # Send to room group
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message_notification',
                'data': message_data
            }
        )
        
        # Also send to individual user notification channels
        for participant in room.participants.all():
            if participant.id != message.sender.id:  # Don't send to sender
                user_group = f'user_notifications_{participant.id}'
                async_to_sync(channel_layer.group_send)(
                    user_group,
                    {
                        'type': 'chat_message_notification',
                        'data': {
                            **message_data,
                            'room_name': room.name,
                            'room_type': room.room_type
                        }
                    }
                )
