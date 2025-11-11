from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('admin-dashboard/', views.admin_dashboard, name='dashboard'),
    # Player URLs (Admin)
    path('admin-dashboard/players/', views.PlayerListView.as_view(), name='player_list'),
    # Dungeon URLs
    path('admin-dashboard/dungeons/', views.DungeonListView.as_view(), name='dungeon_list'),
    path('admin-dashboard/dungeons/create/', views.DungeonCreateView.as_view(), name='dungeon_create'),
    path('admin-dashboard/dungeons/<int:pk>/edit/', views.DungeonUpdateView.as_view(), name='dungeon_update'),
    path('admin-dashboard/dungeons/<int:pk>/delete/', views.dungeon_delete, name='dungeon_delete'),
    path('admin-dashboard/dungeons/<int:dungeon_pk>/attendance/', views.attendance_update, name='attendance_update'),
    # Sidequest URLs (Admin)
    path('admin-dashboard/sidequests/', views.SidequestListView.as_view(), name='sidequest_list'),
    path('admin-dashboard/sidequests/create/', views.SidequestCreateView.as_view(), name='sidequest_create'),
    path('admin-dashboard/sidequests/<int:pk>/edit/', views.SidequestUpdateView.as_view(), name='sidequest_update'),
    path('admin-dashboard/sidequests/<int:pk>/delete/', views.sidequest_delete, name='sidequest_delete'),
    path('admin-dashboard/sidequests/<int:sidequest_pk>/submissions/', views.sidequest_submissions, name='sidequest_submissions'),
    path('admin-dashboard/sidequests/submissions/<int:submission_pk>/grade/', views.grade_submission, name='grade_submission'),
    # Boss URLs (Admin)
    path('admin-dashboard/bosses/', views.BossListView.as_view(), name='boss_list'),
    path('admin-dashboard/bosses/create/', views.BossCreateView.as_view(), name='boss_create'),
    path('admin-dashboard/bosses/<int:pk>/edit/', views.BossUpdateView.as_view(), name='boss_update'),
    path('admin-dashboard/bosses/<int:pk>/delete/', views.boss_delete, name='boss_delete'),
    # Punishment URLs (Admin)
    path('admin-dashboard/punishments/', views.PunishmentListView.as_view(), name='punishment_list'),
    path('admin-dashboard/punishments/create/', views.PunishmentCreateView.as_view(), name='punishment_create'),
    path('admin-dashboard/punishments/<int:pk>/edit/', views.PunishmentUpdateView.as_view(), name='punishment_update'),
    path('admin-dashboard/punishments/<int:pk>/delete/', views.punishment_delete, name='punishment_delete'),
    path('admin-dashboard/punishments/<int:pk>/resolve/', views.resolve_punishment, name='punishment_resolve'),
    # Status Effect URLs (Admin)
    path('admin-dashboard/status-effects/', views.StatusEffectListView.as_view(), name='status_effect_list'),
    # Analytics & Reporting URLs
    path('admin-dashboard/analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('admin-dashboard/export/player-progress-csv/', views.export_player_progress_csv, name='export_player_progress_csv'),
    path('admin-dashboard/export/grades-pdf/', views.export_grades_pdf, name='export_grades_pdf'),
    path('admin-dashboard/export/analytics-excel/', views.export_analytics_excel, name='export_analytics_excel'),
]

