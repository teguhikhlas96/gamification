from django.urls import path
from . import views
from core import views as core_views

app_name = 'player'

urlpatterns = [
    path('player-dashboard/', views.player_dashboard, name='dashboard'),
    path('profile/', views.player_profile, name='profile'),
    path('exp-history/', views.exp_history, name='exp_history'),
    path('punishment-history/', views.punishment_history, name='punishment_history'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    # AJAX endpoints
    path('ajax/stats/', views.ajax_user_stats, name='ajax_stats'),
    path('ajax/activities/', views.ajax_recent_activities, name='ajax_activities'),
    # Sidequest URLs (Player)
    path('sidequests/', core_views.player_sidequest_list, name='sidequest_list'),
    path('sidequests/<int:sidequest_pk>/submit/', core_views.submit_sidequest, name='submit_sidequest'),
    path('submissions/<int:submission_pk>/', core_views.submission_status, name='submission_status'),
    # Dungeon URLs (Player)
    path('dungeons/', core_views.player_dungeon_list, name='dungeon_list'),
    path('dungeons/<int:dungeon_pk>/', core_views.player_dungeon_detail, name='dungeon_detail'),
    # Dashboard card details (Player)
    path('exp-summary/', views.exp_summary, name='exp_summary'),
    path('exp-lost/', views.exp_lost, name='exp_lost'),
    path('honor-history/', views.honor_history, name='honor_history'),
    path('recent-activities/', views.recent_activities, name='recent_activities'),
]

