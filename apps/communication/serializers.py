from rest_framework import serializers
from django.db.models import Count, Q, Max
from apps.users.serializers import UserSerializer
from .models import ChatRoom, Message, MessageRead


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for text messages"""
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 
            'content', 
            'sender', 
            'sender_name', 
            'sender_role',
            'created_at', 
            'is_edited', 
            'edited_at',
            'is_system_message'
        ]
        read_only_fields = ['sender', 'created_at', 'is_edited', 'edited_at']
    
    def create(self, validated_data):
        """Set sender from request context"""
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class ChatRoomListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for chat room lists"""
    participant_count = serializers.IntegerField(read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id',
            'name',
            'room_type',
            'participant_count',
            'unread_count',
            'last_message_preview',
            'last_message_at',
            'created_at'
        ]
    
    def get_unread_count(self, obj):
        """Calculate unread messages count"""
        user = self.context['request'].user
        try:
            read_status = MessageRead.objects.get(user=user, room=obj)
            if read_status.last_read_message:
                return obj.messages.filter(
                    created_at__gt=read_status.last_read_message.created_at
                ).count()
        except MessageRead.DoesNotExist:
            pass
        
        # If no read status, all messages are unread
        return obj.message_count
    
    def get_last_message_preview(self, obj):
        """Get preview of last message"""
        last_message = obj.messages.select_related('sender').last()
        if last_message:
            return {
                'content': last_message.content[:100],
                'sender_name': last_message.sender.username,
                'created_at': last_message.created_at
            }
        return None


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual chat room"""
    participants = UserSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id',
            'name',
            'room_type',
            'participants',
            'created_by',
            'created_by_name',
            'is_active',
            'message_count',
            'last_message_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'last_message_at']


class CreateChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for creating new chat rooms"""
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ChatRoom
        fields = ['name', 'room_type', 'participant_ids']
    
    def create(self, validated_data):
        """Create chat room with participants"""
        participant_ids = validated_data.pop('participant_ids', [])
        user = self.context['request'].user
        
        # Set school and creator
        validated_data['school'] = user.school
        validated_data['created_by'] = user
        
        # Create room
        room = super().create(validated_data)
        
        # Add creator as participant
        room.participants.add(user)
        
        # Add other participants
        if participant_ids:
            # Validate all participants are from same school
            from apps.users.models import User
            participants = User.objects.filter(
                id__in=participant_ids,
                school=user.school
            )
            room.participants.add(*participants)
        
        return room


class MessageReadSerializer(serializers.ModelSerializer):
    """Serializer for message read status"""
    
    class Meta:
        model = MessageRead
        fields = ['user', 'room', 'last_read_message', 'last_read_at']
        read_only_fields = ['last_read_at']