from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from core.models import ExpLog, Level, Punishment, StatusEffect, Dungeon, Attendance, SidequestSubmission, Boss
from core.services import check_honor_privileges
from core.services import PLAGIARISM_RULES, CHEATING_RULES, ABSENCE_RULES


@login_required
def player_dashboard(request):
    """Dashboard untuk player dengan statistik lengkap"""
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    user = request.user
    
    # Get current level info
    try:
        current_level_obj = Level.objects.get(level=user.current_level)
        next_level_obj = Level.objects.filter(level__gt=user.current_level).order_by('level').first()
        
        if next_level_obj:
            exp_for_current_level = current_level_obj.exp_required
            exp_for_next_level = next_level_obj.exp_required
            exp_needed = exp_for_next_level - user.total_exp
            exp_progress = ((user.total_exp - exp_for_current_level) / (exp_for_next_level - exp_for_current_level) * 100) if (exp_for_next_level - exp_for_current_level) > 0 else 0
        else:
            exp_for_current_level = current_level_obj.exp_required
            exp_for_next_level = user.total_exp
            exp_needed = 0
            exp_progress = 100
    except Level.DoesNotExist:
        exp_for_current_level = 0
        exp_for_next_level = 1000
        exp_needed = 1000 - user.total_exp
        exp_progress = (user.total_exp / 1000 * 100) if 1000 > 0 else 0
    
    # Get statistics
    total_exp_earned = ExpLog.objects.filter(user=user, exp_earned__gt=0).aggregate(Sum('exp_earned'))['exp_earned__sum'] or 0
    total_exp_lost = abs(ExpLog.objects.filter(user=user, exp_earned__lt=0).aggregate(Sum('exp_earned'))['exp_earned__sum'] or 0)
    
    # Activity distribution
    activity_stats = ExpLog.objects.filter(user=user).values('activity_type').annotate(
        total=Sum('exp_earned'),
        count=Count('id')
    ).order_by('-total')
    
    # Recent activities (last 10)
    recent_activities = ExpLog.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Active status effects
    active_status_effects = StatusEffect.objects.filter(user=user, is_active=True)
    
    # Active punishments
    active_punishments = Punishment.objects.filter(user=user, resolved=False)
    
    # Honor privileges
    honor_privileges = check_honor_privileges(user)
    
    # Recent achievements (level ups)
    recent_level_ups = ExpLog.objects.filter(
        user=user,
        activity_type='bonus',
        description__icontains='Level Up'
    ).order_by('-created_at')[:5]
    
    # Stats for charts
    # EXP growth (last 30 days)
    # EXP growth (last 30 days) - gunakan hanya EXP positif (earned) agar tidak ter-cancel oleh EXP negatif
    today = timezone.localdate()
    start_date = today - timedelta(days=29)  # 30 hari termasuk hari ini

    raw_growth = (
        ExpLog.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            exp_earned__gt=0  # hanya exp positif
        )
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total_exp=Sum('exp_earned'))
        .order_by('day')
    )

    # Buat peta day -> total_exp dan isi 0 untuk hari tanpa data
    day_to_total = {str(item['day']): (item['total_exp'] or 0) for item in raw_growth}

    exp_growth_chart_data = []
    for i in range(30):
        d = start_date + timedelta(days=i)
        key = d.strftime('%Y-%m-%d')
        exp_growth_chart_data.append({
            'day': key,
            'total_exp': day_to_total.get(key, 0)
        })
    
    # Activity distribution
    activity_distribution = ExpLog.objects.filter(user=user).values('activity_type').annotate(
        count=Count('id')
    )
    
    # Format untuk Chart.js
    activity_chart_data = []
    for item in activity_distribution:
        activity_chart_data.append({
            'activity_type': item['activity_type'],
            'count': item['count']
        })
    
    context = {
        'user': user,
        'exp_for_current_level': exp_for_current_level,
        'exp_for_next_level': exp_for_next_level,
        'exp_needed': exp_needed,
        'exp_progress': min(exp_progress, 100),
        'total_exp_earned': total_exp_earned,
        'total_exp_lost': total_exp_lost,
        'activity_stats': activity_stats,
        'recent_activities': recent_activities,
        'active_status_effects': active_status_effects,
        'active_punishments': active_punishments,
        'honor_privileges': honor_privileges,
        'recent_level_ups': recent_level_ups,
        'exp_growth_data': exp_growth_chart_data,
        'activity_distribution': activity_chart_data,
    }
    
    return render(request, 'player/dashboard.html', context)


@login_required
def player_profile(request):
    """Profile page untuk player dengan achievements"""
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    user = request.user
    
    # Get all statistics
    total_dungeons_attended = Attendance.objects.filter(user=user, attended=True).count()
    total_sidequests_submitted = SidequestSubmission.objects.filter(user=user).count()
    total_sidequests_graded = SidequestSubmission.objects.filter(user=user, grade__isnull=False).count()
    total_boss_battles = Boss.objects.filter(user=user).count()
    total_punishments = Punishment.objects.filter(user=user).count()
    resolved_punishments = Punishment.objects.filter(user=user, resolved=True).count()
    
    # Calculate achievements (simple achievements based on stats)
    achievements = []
    
    if user.current_level >= 5:
        achievements.append({'name': 'Rising Star', 'description': 'Reached Level 5', 'icon': '⭐'})
    if user.current_level >= 10:
        achievements.append({'name': 'Veteran', 'description': 'Reached Level 10', 'icon': '🏆'})
    if total_dungeons_attended >= 10:
        achievements.append({'name': 'Dedicated Student', 'description': 'Attended 10+ Dungeons', 'icon': '📚'})
    if total_sidequests_submitted >= 5:
        achievements.append({'name': 'Quest Master', 'description': 'Submitted 5+ Sidequests', 'icon': '📝'})
    if total_boss_battles >= 3:
        achievements.append({'name': 'Boss Slayer', 'description': 'Completed 3+ Boss Battles', 'icon': '⚔️'})
    if user.honor_points >= 800:
        achievements.append({'name': 'Exalted', 'description': 'Reached Exalted Honor Tier', 'icon': '👑'})
    if resolved_punishments > 0 and total_punishments == resolved_punishments:
        achievements.append({'name': 'Redeemed', 'description': 'Resolved All Punishments', 'icon': '✨'})
    
    # Honor privileges
    honor_privileges = check_honor_privileges(user)
    
    context = {
        'user': user,
        'total_dungeons_attended': total_dungeons_attended,
        'total_sidequests_submitted': total_sidequests_submitted,
        'total_sidequests_graded': total_sidequests_graded,
        'total_boss_battles': total_boss_battles,
        'total_punishments': total_punishments,
        'resolved_punishments': resolved_punishments,
        'achievements': achievements,
        'honor_privileges': honor_privileges,
    }
    
    return render(request, 'player/profile.html', context)


@login_required
def exp_history(request):
    """EXP history log untuk player"""
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    user = request.user
    
    # Get all EXP logs (optimized query)
    exp_logs = ExpLog.objects.filter(user=user).select_related('user').order_by('-created_at')
    
    # Filter by activity type if provided
    activity_type = request.GET.get('activity_type', '')
    if activity_type:
        exp_logs = exp_logs.filter(activity_type=activity_type)
    
    # Pagination (optional, bisa ditambahkan)
    from django.core.paginator import Paginator
    paginator = Paginator(exp_logs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Activity type filter options
    activity_types = ExpLog.ACTIVITY_TYPES
    
    context = {
        'user': user,
        'exp_logs': page_obj,
        'activity_types': activity_types,
        'selected_activity_type': activity_type,
    }
    
    return render(request, 'player/exp_history.html', context)


@login_required
def punishment_history(request):
    """Punishment history untuk player"""
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    user = request.user
    
    # Get all punishments (optimized query)
    punishments = Punishment.objects.filter(user=user).select_related('created_by').order_by('-created_at')
    
    # Get active status effects (optimized query)
    active_status_effects = StatusEffect.objects.filter(user=user, is_active=True).order_by('-start_date')
    
    context = {
        'user': user,
        'punishments': punishments,
        'active_status_effects': active_status_effects,
    }
    
    return render(request, 'player/punishment_history.html', context)


@login_required
def leaderboard(request):
    """Leaderboard untuk semua players dengan query optimization dan caching"""
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    # Get leaderboard with caching (5 minutes cache)
    from core.utils import get_or_set_cache
    
    def get_leaderboard_data():
        return list(User.objects.filter(role='player').only(
            'username', 'current_level', 'total_exp', 'honor_points', 'id'
        ).order_by('-current_level', '-total_exp', '-honor_points'))
    
    players = get_or_set_cache('leaderboard_all_players', get_leaderboard_data, timeout=300)
    
    # Get current user's rank
    user_rank = None
    for idx, player in enumerate(players, start=1):
        if player.id == request.user.id:
            user_rank = idx
            break
    
    # Top 10 players
    top_players = players[:10]
    
    context = {
        'players': players,
        'top_players': top_players,
        'user_rank': user_rank,
        'current_user': request.user,
    }
    
    return render(request, 'player/leaderboard.html', context)


# AJAX Views untuk real-time updates
@login_required
def ajax_user_stats(request):
    """AJAX endpoint untuk mendapatkan user stats real-time"""
    if request.user.is_admin():
        return JsonResponse({'error': 'Admin tidak memiliki stats'}, status=403)
    
    user = request.user
    user.refresh_from_db()  # Refresh dari database
    
    # Get current level info
    try:
        current_level_obj = Level.objects.get(level=user.current_level)
        next_level_obj = Level.objects.filter(level__gt=user.current_level).order_by('level').first()
        
        if next_level_obj:
            exp_for_current_level = current_level_obj.exp_required
            exp_for_next_level = next_level_obj.exp_required
            exp_needed = exp_for_next_level - user.total_exp
            exp_progress = ((user.total_exp - exp_for_current_level) / (exp_for_next_level - exp_for_current_level) * 100) if (exp_for_next_level - exp_for_current_level) > 0 else 0
        else:
            exp_for_current_level = current_level_obj.exp_required
            exp_for_next_level = user.total_exp
            exp_needed = 0
            exp_progress = 100
    except Level.DoesNotExist:
        exp_for_current_level = 0
        exp_for_next_level = 1000
        exp_needed = 1000 - user.total_exp
        exp_progress = (user.total_exp / 1000 * 100) if 1000 > 0 else 0
    
    # Check for new level ups
    recent_level_up = ExpLog.objects.filter(
        user=user,
        activity_type='bonus',
        description__icontains='Level Up',
        created_at__gte=timezone.now() - timedelta(seconds=5)
    ).first()
    
    level_up_info = None
    if recent_level_up:
        level_up_info = {
            'message': recent_level_up.description,
            'new_level': user.current_level,
        }
    
    # Get honor privileges
    honor_privileges = check_honor_privileges(user)
    
    return JsonResponse({
        'current_exp': user.current_exp,
        'total_exp': user.total_exp,
        'current_level': user.current_level,
        'honor_points': user.honor_points,
        'exp_progress': round(exp_progress, 2),
        'exp_needed': exp_needed,
        'level_up': level_up_info,
        'honor_tier': honor_privileges['honor_tier'],
    })


@login_required
def ajax_recent_activities(request):
    """AJAX endpoint untuk mendapatkan recent activities"""
    if request.user.is_admin():
        return JsonResponse({'error': 'Admin tidak memiliki activities'}, status=403)
    
    user = request.user
    
    # Get last 5 activities
    recent_activities = ExpLog.objects.filter(user=user).order_by('-created_at')[:5]
    
    activities_data = []
    for activity in recent_activities:
        activities_data.append({
            'id': activity.id,
            'activity_type': activity.get_activity_type_display(),
            'exp_earned': activity.exp_earned,
            'description': activity.description,
            'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return JsonResponse({
        'activities': activities_data,
    })


# Detail pages for dashboard cards
@login_required
def exp_summary(request):
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    user = request.user
    logs = ExpLog.objects.filter(user=user, exp_earned__gt=0).order_by('-created_at')
    total_earned = logs.aggregate(Sum('exp_earned'))['exp_earned__sum'] or 0
    by_activity = logs.values('activity_type').annotate(total=Sum('exp_earned'), count=Count('id')).order_by('-total')
    levels = Level.objects.all().order_by('level')
    
    context = {
        'user': user,
        'total_earned': total_earned,
        'by_activity': list(by_activity),
        'logs': logs[:100],
        'levels': levels,
    }
    return render(request, 'player/exp_summary.html', context)


@login_required
def exp_lost(request):
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    user = request.user
    logs = ExpLog.objects.filter(user=user, exp_earned__lt=0).order_by('-created_at')
    total_lost = abs(logs.aggregate(Sum('exp_earned'))['exp_earned__sum'] or 0)
    
    context = {
        'user': user,
        'total_lost': total_lost,
        'logs': logs[:100],
    }
    return render(request, 'player/exp_lost.html', context)


@login_required
def honor_history(request):
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    user = request.user
    level_up_logs = ExpLog.objects.filter(user=user, activity_type='bonus', description__icontains='Level Up').order_by('-created_at')
    punishments = Punishment.objects.filter(user=user).order_by('-created_at')
    inferred = []
    for p in punishments:
        honor_change = 0
        if p.type == 'plagiarism':
            rules = PLAGIARISM_RULES.get(p.severity, {})
            honor_change = -int(rules.get('honor_loss', 0))
        elif p.type == 'cheating':
            boss_type = (p.evidence or {}).get('boss_type', 'mini_boss')
            rules = CHEATING_RULES.get(boss_type, {})
            honor_change = -int(rules.get('honor_loss', 0))
        elif p.type == 'absence':
            honor_change = -int(ABSENCE_RULES.get('honor_loss', 0))
        inferred.append({'punishment': p, 'honor_change': honor_change})
    
    context = {
        'user': user,
        'level_up_logs': level_up_logs[:50],
        'punishments_with_honor': inferred[:100],
        'current_honor': user.honor_points,
    }
    return render(request, 'player/honor_history.html', context)


@login_required
def recent_activities(request):
    if request.user.is_admin():
        return redirect('admin_dashboard:dashboard')
    
    user = request.user
    try:
        limit = int(request.GET.get('limit', '10'))
        limit = max(1, min(100, limit))
    except ValueError:
        limit = 10
    logs = ExpLog.objects.filter(user=user).order_by('-created_at')[:limit]
    
    context = {
        'user': user,
        'logs': logs,
        'limit': limit,
    }
    return render(request, 'player/recent_activities.html', context)
