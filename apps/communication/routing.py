from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/chat/room/(?P<room_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    # Ruta de prueba sin autenticación
    re_path(r'ws/test/$', consumers.TestConsumer.as_asgi()),
    # Ruta de prueba con autenticación
    re_path(r'ws/test-auth/(?P<room_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]