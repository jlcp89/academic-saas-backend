import json
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from urllib.parse import parse_qs
import logging

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT tokens
    """
    
    async def __call__(self, scope, receive, send):
        # Extract token from query parameters
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        logger.info(f"🔍 [WEBSOCKET DEBUG] JWT Auth attempt - Token present: {bool(token)}")
        
        if token:
            try:
                # Validate JWT token
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                
                # Get user from database
                user = await self.get_user(user_id)
                if user:
                    scope['user'] = user
                    logger.info(f"✅ [WEBSOCKET DEBUG] JWT Auth successful for user: {user.username}")
                else:
                    scope['user'] = AnonymousUser()
                    logger.warning(f"❌ [WEBSOCKET DEBUG] JWT Auth failed - user not found: {user_id}")
            except TokenError as e:
                scope['user'] = AnonymousUser()
                logger.warning(f"❌ [WEBSOCKET DEBUG] JWT Auth failed - invalid token: {e}")
            except Exception as e:
                scope['user'] = AnonymousUser()
                logger.error(f"❌ [WEBSOCKET DEBUG] JWT Auth error: {e}")
        else:
            scope['user'] = AnonymousUser()
            logger.warning(f"❌ [WEBSOCKET DEBUG] JWT Auth failed - no token provided")
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None 