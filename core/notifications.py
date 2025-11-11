"""
Notification system untuk real-time notifications via WebSocket
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json


def send_notification(user_id, message, notification_type='info', data=None):
    """
    Send real-time notification to specific user
    
    Args:
        user_id: User ID to send notification to
        message: Notification message
        notification_type: Type of notification ('info', 'success', 'warning', 'error', 'level_up', 'achievement', 'sidequest', 'punishment')
        data: Additional data to send with notification
    """
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {
                'type': 'notification_message',
                'message': message,
                'notification_type': notification_type,
                'data': data or {}
            }
        )


def send_level_up_notification(user_id, old_level, new_level, honor_points_bonus=0):
    """Send level up notification"""
    send_notification(
        user_id=user_id,
        message=f'🎉 Level Up! You reached Level {new_level}!',
        notification_type='level_up',
        data={
            'old_level': old_level,
            'new_level': new_level,
            'honor_points_bonus': honor_points_bonus
        }
    )


def send_achievement_notification(user_id, achievement_name, achievement_description, icon='🏆'):
    """Send achievement unlocked notification"""
    send_notification(
        user_id=user_id,
        message=f'{icon} Achievement Unlocked: {achievement_name}!',
        notification_type='achievement',
        data={
            'achievement_name': achievement_name,
            'achievement_description': achievement_description,
            'icon': icon
        }
    )


def send_sidequest_notification(user_id, sidequest_title, sidequest_id):
    """Send new sidequest available notification"""
    send_notification(
        user_id=user_id,
        message=f'📝 New Sidequest Available: {sidequest_title}',
        notification_type='sidequest',
        data={
            'sidequest_title': sidequest_title,
            'sidequest_id': sidequest_id
        }
    )


def send_punishment_notification(user_id, punishment_type, severity, exp_penalty):
    """Send punishment applied notification"""
    send_notification(
        user_id=user_id,
        message=f'⚠️ Punishment Applied: {punishment_type} ({severity}) - {exp_penalty} EXP penalty',
        notification_type='punishment',
        data={
            'punishment_type': punishment_type,
            'severity': severity,
            'exp_penalty': exp_penalty
        }
    )


def broadcast_leaderboard_update():
    """Broadcast leaderboard update to all connected clients"""
    channel_layer = get_channel_layer()
    if channel_layer:
        from accounts.models import User
        
        # Get updated leaderboard data
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
        
        async_to_sync(channel_layer.group_send)(
            'leaderboard_updates',
            {
                'type': 'leaderboard_update',
                'data': leaderboard
            }
        )

