from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.organizations.models import School


class ChatRoom(models.Model):
    """Simple chat room model for text-only messaging"""
    
    ROOM_TYPES = [
        ('DIRECT', 'Direct Message'),
        ('GROUP', 'Group Chat'),
        ('CLASS', 'Class Room'),
        ('ANNOUNCEMENT', 'Announcement'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='chat_rooms')
    name = models.CharField(max_length=255)
    room_type = models.CharField(max_length=12, choices=ROOM_TYPES, default='GROUP')
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_chat_rooms')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Denormalized fields for performance
    last_message_at = models.DateTimeField(null=True, blank=True)
    message_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['school', '-last_message_at']),
            models.Index(fields=['school', 'room_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"
    
    def add_participant(self, user):
        """Add a user to the chat room"""
        if user.school != self.school and user.role != User.Role.SUPERADMIN:
            raise ValueError("User must be from the same school")
        self.participants.add(user)
    
    def remove_participant(self, user):
        """Remove a user from the chat room"""
        self.participants.remove(user)


class Message(models.Model):
    """Simple text message model"""
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    
    # For system messages
    is_system_message = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        """Update room's last message timestamp on save"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update room's denormalized fields
            self.room.last_message_at = self.created_at
            self.room.message_count = models.F('message_count') + 1
            self.room.save(update_fields=['last_message_at', 'message_count'])


class MessageRead(models.Model):
    """Track which messages have been read by which users"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_messages')
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='read_receipts')
    last_read_message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    last_read_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'room')
        indexes = [
            models.Index(fields=['user', 'room']),
        ]
    
    def __str__(self):
        return f"{self.user.username} read up to message {self.last_read_message_id}"
