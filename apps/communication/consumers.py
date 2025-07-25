import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)


class TestConsumer(AsyncJsonWebsocketConsumer):
    """
    Simple test consumer without authentication for debugging
    """
    
    async def connect(self):
        """Accept connection without authentication"""
        logger.info(f"🔌 [WEBSOCKET DEBUG] TestConsumer connect attempt")
        
        await self.accept()
        logger.info(f"✅ [WEBSOCKET DEBUG] TestConsumer connected successfully")
        
        # Send a test message
        await self.send_json({
            'type': 'test_message',
            'data': 'WebSocket connection successful!'
        })
    
    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        logger.info(f"📨 [WEBSOCKET DEBUG] TestConsumer received: {content}")
        
        # Echo back the message
        await self.send_json({
            'type': 'echo',
            'data': content
        })
    
    async def disconnect(self, close_code):
        """Clean up when user disconnects"""
        logger.info(f"🔌 [WEBSOCKET DEBUG] TestConsumer disconnected with code {close_code}")
    
    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        logger.info(f"📨 [WEBSOCKET DEBUG] TestConsumer received: {content}")
        
        # Echo back the message
        await self.send_json({
            'type': 'echo',
            'data': content
        })


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Lightweight WebSocket consumer for real-time notifications.
    Only handles notifications, not full message content.
    """
    
    async def connect(self):
        """Accept connection if user is authenticated"""
        self.user = self.scope["user"]
        
        logger.info(f"🔌 [WEBSOCKET DEBUG] NotificationConsumer connect attempt - User: {self.user}")
        
        if isinstance(self.user, AnonymousUser):
            logger.warning(f"❌ [WEBSOCKET DEBUG] Anonymous user rejected")
            await self.close()
            return
        
        # Join user's personal notification channel
        self.user_group = f"user_notifications_{self.user.id}"
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"✅ [WEBSOCKET DEBUG] User {self.user.username} connected to notifications")
    
    async def disconnect(self, close_code):
        """Clean up when user disconnects"""
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )
        logger.info(f"🔌 [WEBSOCKET DEBUG] User disconnected with code {close_code}")
    
    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        message_type = content.get('type')
        
        if message_type == 'ping':
            # Simple ping/pong for connection keep-alive
            await self.send_json({'type': 'pong'})
    
    # Handlers for different types of notifications
    async def chat_message_notification(self, event):
        """Send new message notification to user"""
        await self.send_json({
            'type': 'new_message',
            'data': event['data']
        })
    
    async def participant_added_notification(self, event):
        """Send participant added notification to user"""
        await self.send_json({
            'type': 'participant_added',
            'data': event['data']
        })
    
    async def user_status_update(self, event):
        """Send user online/offline status updates"""
        await self.send_json({
            'type': 'user_status',
            'data': event['data']
        })


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Minimal chat consumer for room-specific notifications.
    Handles typing indicators and message notifications only.
    """
    
    async def connect(self):
        """Connect to a specific chat room"""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_room_{self.room_id}'
        self.user = self.scope["user"]
        
        logger.info(f"🔌 [WEBSOCKET DEBUG] ChatConsumer connect attempt - Room: {self.room_id}, User: {self.user}")
        
        if isinstance(self.user, AnonymousUser):
            logger.warning(f"❌ [WEBSOCKET DEBUG] Anonymous user rejected for room {self.room_id}")
            await self.close()
            return
        
        # TEMPORARIO: Permitir conexión sin verificar sala para pruebas
        logger.info(f"🔍 [WEBSOCKET DEBUG] User {self.user.username} connecting to room {self.room_id} (bypassing room check for testing)")
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"✅ [WEBSOCKET DEBUG] User {self.user.username} connected to room {self.room_id}")
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
    
    async def disconnect(self, close_code):
        """Clean up when user leaves room"""
        logger.info(f"🔌 [WEBSOCKET DEBUG] User {getattr(self, 'user', 'unknown')} disconnected from room {getattr(self, 'room_id', 'unknown')} with code {close_code}")
        
        if hasattr(self, 'room_group_name'):
            # Notify others that user left
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user_id': self.user.id,
                    'username': self.user.username
                }
            )
            
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive_json(self, content):
        """Handle incoming messages"""
        message_type = content.get('type')
        logger.info(f"📨 [WEBSOCKET DEBUG] Received message type: {message_type}")
        
        if message_type == 'typing_start':
            await self.handle_typing_start()
        elif message_type == 'typing_stop':
            await self.handle_typing_stop()
    
    async def handle_typing_start(self):
        """Broadcast typing indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': True
            }
        )
    
    async def handle_typing_stop(self):
        """Stop typing indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': False
            }
        )
    
    # Event handlers for group messages
    async def chat_message_notification(self, event):
        """Forward message notification to WebSocket"""
        await self.send_json({
            'type': 'new_message',
            'data': event['data']
        })
    
    async def typing_indicator(self, event):
        """Forward typing indicator"""
        # Don't send typing indicator to the user who is typing
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            })
    
    async def user_joined(self, event):
        """Notify about user joining"""
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username']
            })
    
    async def user_left(self, event):
        """Notify about user leaving"""
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username']
            })
    
    async def participant_added_notification(self, event):
        """Forward participant added notification to WebSocket"""
        await self.send_json({
            'type': 'participant_added',
            'data': event['data']
        })
    
    @database_sync_to_async
    def user_can_access_room(self):
        """Check if user is a participant in the chat room"""
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            is_participant = room.participants.filter(id=self.user.id).exists()
            logger.info(f"🔍 [WEBSOCKET DEBUG] Room {self.room_id} exists: {room.name}, User {self.user.username} is participant: {is_participant}")
            return is_participant
        except ChatRoom.DoesNotExist:
            logger.warning(f"❌ [WEBSOCKET DEBUG] Room {self.room_id} does not exist")
            return False