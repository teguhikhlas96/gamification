"""
WebSocket URL routing untuk Django Channels
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/(?P<user_id>\w+)/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/leaderboard/$', consumers.LeaderboardConsumer.as_asgi()),
    re_path(r'ws/online-status/$', consumers.OnlineStatusConsumer.as_asgi()),
]

