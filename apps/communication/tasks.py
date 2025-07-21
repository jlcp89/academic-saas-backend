from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_message_notification(room_id, message_id):
    """
    Send lightweight notification to room participants about new message.
    This is a simple implementation that notifies users without heavy processing.
    """
    try:
        from .models import ChatRoom, Message
        
        # Get message and room info
        message = Message.objects.select_related('sender').get(id=message_id)
        room = ChatRoom.objects.get(id=room_id)
        
        # Prepare notification data (lightweight)
        notification_data = {
            'type': 'new_message',
            'room_id': room_id,
            'message_id': message_id,
            'sender_name': message.sender.username,
            'preview': message.content[:100] + '...' if len(message.content) > 100 else message.content,
            'timestamp': message.created_at.isoformat()
        }
        
        # Get channel layer for WebSocket communication
        channel_layer = get_channel_layer()
        
        if channel_layer:
            # Send to room group (all participants)
            async_to_sync(channel_layer.group_send)(
                f"chat_room_{room_id}",
                {
                    'type': 'chat_message_notification',
                    'data': notification_data
                }
            )
            
            # Also send to individual user notification channels
            for participant in room.participants.all():
                if participant.id != message.sender.id:  # Don't notify sender
                    async_to_sync(channel_layer.group_send)(
                        f"user_notifications_{participant.id}",
                        {
                            'type': 'chat_message_notification',
                            'data': notification_data
                        }
                    )
            
            logger.info(f"Notification sent for message {message_id} in room {room_id}")
        else:
            logger.warning("Channel layer not available, skipping WebSocket notification")
            
    except Exception as e:
        logger.error(f"Error sending message notification: {str(e)}")
        # Don't retry on failure to avoid spamming
        raise


@shared_task
def mark_room_as_updated(room_id):
    """
    Update room's last activity timestamp.
    This helps with sorting rooms by recent activity.
    """
    try:
        from django.utils import timezone
        from .models import ChatRoom
        
        ChatRoom.objects.filter(id=room_id).update(
            last_message_at=timezone.now()
        )
        
        logger.info(f"Updated last activity for room {room_id}")
        
    except Exception as e:
        logger.error(f"Error updating room activity: {str(e)}")


@shared_task
def cleanup_old_read_receipts():
    """
    Periodic task to clean up old read receipts for deleted messages.
    Run this daily to maintain database performance.
    """
    try:
        from .models import MessageRead
        
        # Delete read receipts where the message no longer exists
        deleted_count = MessageRead.objects.filter(
            last_read_message__isnull=True
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} orphaned read receipts")
        
    except Exception as e:
        logger.error(f"Error cleaning up read receipts: {str(e)}")