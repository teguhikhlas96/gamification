"""
WebSocket consumers untuk real-time features
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer untuk real-time notifications"""
    
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'notifications_{self.user_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to notifications'
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')
        
        # Echo message back (for testing)
        await self.send(text_data=json.dumps({
            'type': 'echo',
            'message': message
        }))
    
    # Receive message from room group
    async def notification_message(self, event):
        """Handle notification message from group"""
        message = event['message']
        notification_type = event.get('notification_type', 'info')
        data = event.get('data', {})
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification_type': notification_type,
            'message': message,
            'data': data,
            'timestamp': timezone.now().isoformat()
        }))


class LeaderboardConsumer(AsyncWebsocketConsumer):
    """Consumer untuk live leaderboard updates"""
    
    async def connect(self):
        self.room_group_name = 'leaderboard_updates'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial leaderboard data
        leaderboard_data = await self.get_leaderboard_data()
        await self.send(text_data=json.dumps({
            'type': 'leaderboard_update',
            'data': leaderboard_data
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        # Handle refresh request
        text_data_json = json.loads(text_data)
        if text_data_json.get('action') == 'refresh':
            leaderboard_data = await self.get_leaderboard_data()
            await self.send(text_data=json.dumps({
                'type': 'leaderboard_update',
                'data': leaderboard_data
            }))
    
    async def leaderboard_update(self, event):
        """Handle leaderboard update from group"""
        leaderboard_data = event.get('data', {})
        
        await self.send(text_data=json.dumps({
            'type': 'leaderboard_update',
            'data': leaderboard_data
        }))
    
    @database_sync_to_async
    def get_leaderboard_data(self):
        """Get current leaderboard data"""
        from accounts.models import User
        
        players = User.objects.filter(role='player').order_by(
            '-current_level', '-total_exp', '-honor_points'
        )[:20]
        
        leaderboard = []
        for idx, player in enumerate(players, start=1):
            leaderboard.append({
                'rank': idx,
                'username': player.username,
                'level': player.current_level,
                'total_exp': player.total_exp,
                'honor_points': player.honor_points
            })
        
        return leaderboard


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    """Consumer untuk online status tracking"""
    
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.room_group_name = 'online_status'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Mark user as online
        await self.mark_user_online(self.user.id)
        
        # Broadcast user online status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online'
            }
        )
    
    async def disconnect(self, close_code):
        # Mark user as offline
        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.mark_user_offline(self.user.id)
            
            # Broadcast user offline status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'status': 'offline'
                }
            )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json.get('action')
        
        if action == 'get_online_users':
            online_users = await self.get_online_users()
            await self.send(text_data=json.dumps({
                'type': 'online_users',
                'users': online_users
            }))
    
    async def user_status(self, event):
        """Handle user status update from group"""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))
    
    @database_sync_to_async
    def mark_user_online(self, user_id):
        """Mark user as online"""
        from django.core.cache import cache
        cache.set(f'user_{user_id}_online', True, timeout=300)  # 5 minutes
        cache.set(f'user_{user_id}_last_seen', timezone.now().isoformat(), timeout=300)
    
    @database_sync_to_async
    def mark_user_offline(self, user_id):
        """Mark user as offline"""
        from django.core.cache import cache
        cache.delete(f'user_{user_id}_online')
    
    @database_sync_to_async
    def get_online_users(self):
        """Get list of online users"""
        from django.core.cache import cache
        from accounts.models import User
        
        online_users = []
        players = User.objects.filter(role='player')
        
        for player in players:
            is_online = cache.get(f'user_{player.id}_online', False)
            if is_online:
                last_seen = cache.get(f'user_{player.id}_last_seen', '')
                online_users.append({
                    'id': player.id,
                    'username': player.username,
                    'last_seen': last_seen
                })
        
        return online_users

