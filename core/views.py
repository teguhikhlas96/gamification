from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F, Max
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from datetime import timedelta, datetime
import csv
import json
from accounts.models import User
from core.models import ExpLog, Dungeon, Attendance, Sidequest, SidequestSubmission, Boss, Punishment, StatusEffect, Level
from core.services import add_exp, calculate_final_score, PunishmentService, check_honor_privileges
from core.notifications import send_sidequest_notification, broadcast_leaderboard_update, send_punishment_notification
from core.services import PLAGIARISM_RULES
from core.forms import SidequestForm, SubmissionForm, GradeSubmissionForm, BossForm, PunishmentForm


@login_required
def admin_dashboard(request):
    """Dashboard untuk admin"""
    if not request.user.is_admin():
        return redirect('player:dashboard')
    
    # Get statistics
    total_users = User.objects.count()
    total_players = User.objects.filter(role='player').count()
    total_admins = User.objects.filter(role='admin').count()
    
    # Count active dungeons
    active_dungeons = Dungeon.objects.filter(status='active').count()
    pending_sidequests = 0  # TODO: Implement when Sidequest model is created
    
    # Recent EXP Activities (last 10)
    recent_exp_activities = ExpLog.objects.select_related('user').order_by('-created_at')[:10]
    
    context = {
        'user': request.user,
        'total_users': total_users,
        'total_players': total_players,
        'total_admins': total_admins,
        'active_dungeons': active_dungeons,
        'pending_sidequests': pending_sidequests,
        'recent_exp_activities': recent_exp_activities,
    }
    
    return render(request, 'admin/dashboard.html', context)


# Dungeon Views
@login_required
def player_dungeon_list(request):
    """List dungeons untuk player dengan informasi lebih lengkap"""
    if request.user.is_admin():
        return redirect('admin_dashboard:dungeon_list')

    # Semua dungeon dengan participants count, urutkan yang aktif dan terjadwal lebih dulu
    dungeons = Dungeon.objects.annotate(
        participants_count=Count('attendances', filter=Q(attendances__attended=True))
    ).order_by(
        F('status').desc(nulls_last=True), 'scheduled_date'
    )

    # Daftar dungeon yang dihadiri oleh user (untuk status attended)
    attended_ids = list(
        Attendance.objects.filter(user=request.user, attended=True).values_list('dungeon_id', flat=True)
    )

    context = {
        'dungeons': dungeons,
        'attended_ids': attended_ids,
    }
    return render(request, 'player/dungeon_list.html', context)


@login_required
def player_dungeon_detail(request, dungeon_pk: int):
    """Detail dungeon untuk player"""
    if request.user.is_admin():
        return redirect('admin_dashboard:dungeon_list')

    dungeon = get_object_or_404(Dungeon, pk=dungeon_pk)

    attendance = Attendance.objects.filter(user=request.user, dungeon=dungeon).first()
    participants_count = Attendance.objects.filter(dungeon=dungeon, attended=True).count()

    context = {
        'dungeon': dungeon,
        'attendance': attendance,
        'participants_count': participants_count,
    }
    return render(request, 'player/dungeon_detail.html', context)


class PlayerListView(ListView):
    """List view untuk semua players (Admin)"""
    model = User
    template_name = 'admin/player_list.html'
    context_object_name = 'players'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Tampilkan hanya users dengan role player, dengan pencarian opsional"""
        queryset = User.objects.filter(role='player').order_by('-total_exp', '-current_level', 'username')
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset


class DungeonListView(ListView):
    """List view untuk semua dungeons dengan query optimization"""
    model = Dungeon
    template_name = 'admin/dungeon_list.html'
    context_object_name = 'dungeons'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Optimize query dengan select_related dan prefetch_related"""
        return Dungeon.objects.select_related().prefetch_related('attendances').all()


class DungeonCreateView(CreateView):
    """Create view untuk membuat dungeon baru"""
    model = Dungeon
    template_name = 'admin/dungeon_form.html'
    fields = ['name', 'description', 'scheduled_date', 'status', 'exp_reward']
    success_url = reverse_lazy('admin_dashboard:dungeon_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, f'Dungeon "{form.cleaned_data["name"]}" berhasil dibuat!')
        return super().form_valid(form)


class DungeonUpdateView(UpdateView):
    """Update view untuk mengedit dungeon"""
    model = Dungeon
    template_name = 'admin/dungeon_form.html'
    fields = ['name', 'description', 'scheduled_date', 'status', 'exp_reward']
    success_url = reverse_lazy('admin_dashboard:dungeon_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, f'Dungeon "{form.cleaned_data["name"]}" berhasil diupdate!')
        return super().form_valid(form)


@login_required
def dungeon_delete(request, pk):
    """Delete view untuk menghapus dungeon"""
    if not request.user.is_admin():
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus dungeon.')
        return redirect('admin_dashboard:dungeon_list')
    
    dungeon = get_object_or_404(Dungeon, pk=pk)
    
    if request.method == 'POST':
        dungeon_name = dungeon.name
        dungeon.delete()
        messages.success(request, f'Dungeon "{dungeon_name}" berhasil dihapus!')
        return redirect('admin_dashboard:dungeon_list')
    
    return render(request, 'admin/dungeon_confirm_delete.html', {'dungeon': dungeon})


@login_required
def attendance_update(request, dungeon_pk):
    """View untuk update attendance semua players untuk dungeon tertentu"""
    if not request.user.is_admin():
        messages.error(request, 'Anda tidak memiliki akses untuk mengelola attendance.')
        return redirect('admin_dashboard:dashboard')
    
    dungeon = get_object_or_404(Dungeon, pk=dungeon_pk)
    players = User.objects.filter(role='player')
    
    # Get atau create attendance untuk setiap player
    attendances = []
    for player in players:
        attendance, created = Attendance.objects.get_or_create(
            user=player,
            dungeon=dungeon,
            defaults={'attended': False, 'participation_exp': 0}
        )
        attendances.append(attendance)
    
    if request.method == 'POST':
        try:
            bulk_action = request.POST.get('bulk')
            with transaction.atomic():
                if bulk_action in ('all', 'none'):
                    # Bulk mark all attended or none
                    mark_attended = bulk_action == 'all'
                    updated = 0
                    for attendance in attendances:
                        old_attended = attendance.attended
                        new_attended = mark_attended
                        attendance.attended = new_attended

                        if new_attended and not old_attended:
                            honor_privileges = check_honor_privileges(attendance.user)
                            if not honor_privileges['can_join_dungeon']:
                                # skip give EXP but keep attended False
                                attendance.attended = False
                                attendance.save()
                                continue
                            attendance.participation_exp = dungeon.exp_reward
                            attendance.save()
                            add_exp(
                                user=attendance.user,
                                amount=dungeon.exp_reward,
                                activity_type='participation',
                                description=f"Attended dungeon: {dungeon.name}"
                            )
                            updated += 1
                        elif not new_attended and old_attended:
                            attendance.participation_exp = 0
                            attendance.save()
                            add_exp(
                                user=attendance.user,
                                amount=-dungeon.exp_reward,
                                activity_type='participation',
                                description=f"Removed attendance for dungeon: {dungeon.name}"
                            )
                            updated += 1
                        else:
                            attendance.save()

                        if not new_attended:
                            try:
                                PunishmentService.check_and_apply_absence_punishment(
                                    user=attendance.user,
                                    created_by=request.user
                                )
                            except Exception:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.error('Error checking absence punishment during bulk attendance update')
                    if mark_attended:
                        messages.success(request, f'Semua player ditandai hadir (kecuali yang tidak memenuhi honor). Diperbarui: {updated}')
                    else:
                        messages.success(request, f'Semua player ditandai tidak hadir. Diperbarui: {updated}')
                    return redirect('admin_dashboard:attendance_update', dungeon_pk=dungeon.pk)
                else:
                    # Per-item update (existing behavior)
                    for attendance in attendances:
                        old_attended = attendance.attended
                        new_attended = request.POST.get(f'attended_{attendance.id}') == 'on'
                        attendance.attended = new_attended
                        if new_attended and not old_attended:
                            honor_privileges = check_honor_privileges(attendance.user)
                            if not honor_privileges['can_join_dungeon']:
                                messages.warning(
                                    request,
                                    f'{attendance.user.username} tidak dapat join dungeon karena honor points terlalu rendah. '
                                    f'Attendance tidak diberikan EXP.'
                                )
                                attendance.attended = False
                                attendance.save()
                                continue
                            attendance.participation_exp = dungeon.exp_reward
                            attendance.save()
                            add_exp(
                                user=attendance.user,
                                amount=dungeon.exp_reward,
                                activity_type='participation',
                                description=f"Attended dungeon: {dungeon.name}"
                            )
                        elif not new_attended and old_attended:
                            attendance.participation_exp = 0
                            attendance.save()
                            add_exp(
                                user=attendance.user,
                                amount=-dungeon.exp_reward,
                                activity_type='participation',
                                description=f"Removed attendance for dungeon: {dungeon.name}"
                            )
                        else:
                            attendance.save()
                        if not new_attended:
                            try:
                                PunishmentService.check_and_apply_absence_punishment(
                                    user=attendance.user,
                                    created_by=request.user
                                )
                            except Exception as e:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.error(f'Error checking absence punishment: {str(e)}')
            messages.success(request, f'Attendance untuk "{dungeon.name}" berhasil diupdate!')
            return redirect('admin_dashboard:dungeon_list')
        except Exception as e:
            messages.error(request, f'Error updating attendance: {str(e)}')
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error in attendance_update: {str(e)}', exc_info=True)
            return redirect('admin_dashboard:dungeon_list')
    
    context = {
        'dungeon': dungeon,
        'attendances': attendances,
    }
    
    return render(request, 'admin/attendance_form.html', context)


# Sidequest Views for Admin
class SidequestListView(ListView):
    """List view untuk semua sidequests (Admin) dengan query optimization"""
    model = Sidequest
    template_name = 'admin/sidequest_list.html'
    context_object_name = 'sidequests'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Optimize query dengan prefetch_related untuk submissions"""
        return Sidequest.objects.prefetch_related('submissions').all()


class SidequestCreateView(CreateView):
    """Create view untuk membuat sidequest baru"""
    model = Sidequest
    form_class = SidequestForm
    template_name = 'admin/sidequest_form.html'
    success_url = reverse_lazy('admin_dashboard:sidequest_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        sidequest = form.save()
        messages.success(self.request, f'Sidequest "{sidequest.title}" berhasil dibuat!')
        
        # Send notification to all players if sidequest is active
        if sidequest.status == 'active':
            try:
                from accounts.models import User
                players = User.objects.filter(role='player')
                for player in players:
                    send_sidequest_notification(
                        user_id=player.id,
                        sidequest_title=sidequest.title,
                        sidequest_id=sidequest.id
                    )
            except Exception as e:
                # Silently fail if notification system is not available
                pass
        
        return redirect(self.success_url)


class SidequestUpdateView(UpdateView):
    """Update view untuk mengedit sidequest"""
    model = Sidequest
    form_class = SidequestForm
    template_name = 'admin/sidequest_form.html'
    success_url = reverse_lazy('admin_dashboard:sidequest_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, f'Sidequest "{form.cleaned_data["title"]}" berhasil diupdate!')
        return super().form_valid(form)


@login_required
def sidequest_delete(request, pk):
    """Delete view untuk menghapus sidequest"""
    if not request.user.is_admin():
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus sidequest.')
        return redirect('admin_dashboard:sidequest_list')
    
    sidequest = get_object_or_404(Sidequest, pk=pk)
    
    if request.method == 'POST':
        sidequest_title = sidequest.title
        sidequest.delete()
        messages.success(request, f'Sidequest "{sidequest_title}" berhasil dihapus!')
        return redirect('admin_dashboard:sidequest_list')
    
    return render(request, 'admin/sidequest_confirm_delete.html', {'sidequest': sidequest})


@login_required
def sidequest_submissions(request, sidequest_pk):
    """View untuk melihat semua submissions untuk sidequest tertentu"""
    if not request.user.is_admin():
        messages.error(request, 'Anda tidak memiliki akses untuk melihat submissions.')
        return redirect('player:sidequest_list')
    
    sidequest = get_object_or_404(Sidequest, pk=sidequest_pk)
    submissions = SidequestSubmission.objects.filter(sidequest=sidequest).select_related('user')
    
    context = {
        'sidequest': sidequest,
        'submissions': submissions,
    }
    
    return render(request, 'admin/sidequest_submissions.html', context)


@login_required
def grade_submission(request, submission_pk):
    """View untuk grade submission"""
    if not request.user.is_admin():
        messages.error(request, 'Anda tidak memiliki akses untuk grade submissions.')
        return redirect('player:sidequest_list')
    
    submission = get_object_or_404(SidequestSubmission, pk=submission_pk)
    
    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            with transaction.atomic():
                old_grade = submission.grade
                submission = form.save()
                
                # Jika grade di-set dan sebelumnya belum ada, berikan EXP
                if submission.grade is not None and old_grade is None:
                    exp_reward = submission.get_exp_reward()
                    submission.exp_earned = exp_reward
                    submission.save()
                    
                    # Tambahkan EXP ke user
                    add_exp(
                        user=submission.user,
                        amount=exp_reward,
                        activity_type='assignment',
                        description=f"Graded sidequest: {submission.sidequest.title} (Grade: {submission.grade})"
                    )
                
                messages.success(request, f'Submission dari {submission.user.username} berhasil dinilai!')
                return redirect('admin_dashboard:sidequest_submissions', sidequest_pk=submission.sidequest.pk)
    else:
        form = GradeSubmissionForm(instance=submission)
    
    context = {
        'submission': submission,
        'form': form,
    }
    
    return render(request, 'admin/grade_submission.html', context)


# Sidequest Views for Player
@login_required
def player_sidequest_list(request):
    """List sidequests untuk player"""
    if request.user.is_admin():
        return redirect('admin_dashboard:sidequest_list')
    
    # Get active sidequests
    sidequests = Sidequest.objects.filter(status='active')
    
    # Get user's submissions
    user_submissions = {
        sub.sidequest.pk: sub 
        for sub in SidequestSubmission.objects.filter(user=request.user).select_related('sidequest')
    }
    
    context = {
        'sidequests': sidequests,
        'user_submissions': user_submissions,
    }
    
    return render(request, 'player/sidequest_list.html', context)


@login_required
def submit_sidequest(request, sidequest_pk):
    """View untuk submit sidequest"""
    if request.user.is_admin():
        return redirect('admin_dashboard:sidequest_list')
    
    # Check honor privileges
    honor_privileges = check_honor_privileges(request.user)
    if not honor_privileges['can_submit_sidequest']:
        messages.error(
            request, 
            f'Anda tidak dapat submit sidequest karena honor points terlalu rendah ({request.user.honor_points}). '
            f'Tier: {honor_privileges["honor_tier"]}'
        )
        return redirect('player:sidequest_list')
    
    sidequest = get_object_or_404(Sidequest, pk=sidequest_pk)
    
    # Check jika sudah submit
    existing_submission = SidequestSubmission.objects.filter(
        user=request.user,
        sidequest=sidequest
    ).first()
    
    if existing_submission:
        messages.warning(request, 'Anda sudah mengumpulkan tugas ini.')
        return redirect('player:sidequest_list')
    
    # Check jika sidequest masih active
    if sidequest.status != 'active':
        messages.error(request, 'Sidequest ini tidak aktif.')
        return redirect('player:sidequest_list')
    
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                submission = form.save(commit=False)
                submission.user = request.user
                submission.sidequest = sidequest
                submission.save()
                
                messages.success(request, f'Tugas "{sidequest.title}" berhasil dikumpulkan!')
                return redirect('player:sidequest_list')
        else:
            messages.error(request, 'Terjadi error saat mengumpulkan tugas.')
    else:
        form = SubmissionForm()
    
    context = {
        'sidequest': sidequest,
        'form': form,
    }
    
    return render(request, 'player/submission_form.html', context)


@login_required
def submission_status(request, submission_pk):
    """View untuk melihat status submission"""
    if request.user.is_admin():
        return redirect('admin_dashboard:sidequest_list')
    
    submission = get_object_or_404(SidequestSubmission, pk=submission_pk, user=request.user)
    
    context = {
        'submission': submission,
    }
    
    return render(request, 'player/submission_status.html', context)


# Boss Battle Views for Admin
class BossListView(ListView):
    """List view untuk semua boss battles (Admin)"""
    model = Boss
    template_name = 'admin/boss_list.html'
    context_object_name = 'bosses'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)


class BossCreateView(CreateView):
    """Create view untuk membuat boss battle baru"""
    model = Boss
    form_class = BossForm
    template_name = 'admin/boss_form.html'
    success_url = reverse_lazy('admin_dashboard:boss_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Check honor privileges
        user = form.cleaned_data['user']
        honor_privileges = check_honor_privileges(user)
        
        if not honor_privileges['can_participate_boss']:
            messages.error(
                self.request,
                f'Player {user.username} tidak dapat mengikuti boss battle karena honor points terlalu rendah '
                f'({user.honor_points}). Tier: {honor_privileges["honor_tier"]}'
            )
            return self.form_invalid(form)
        
        # Calculate final score dengan bonus
        base_score = form.cleaned_data['base_score']
        player_level = user.current_level
        
        score_result = calculate_final_score(base_score, player_level)
        
        boss = form.save(commit=False)
        boss.final_score = score_result['final_score']
        boss.bonus_applied = score_result['bonus_applied']
        boss.save()
        
        messages.success(
            self.request, 
            f'Boss battle "{form.cleaned_data["name"]}" berhasil dibuat! '
            f'Final Score: {boss.final_score} (Base: {base_score} + Bonus: {boss.bonus_applied})'
        )
        return redirect(self.success_url)


class BossUpdateView(UpdateView):
    """Update view untuk mengedit boss battle"""
    model = Boss
    form_class = BossForm
    template_name = 'admin/boss_form.html'
    success_url = reverse_lazy('admin_dashboard:boss_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Recalculate final score dengan bonus
        base_score = form.cleaned_data['base_score']
        user = form.cleaned_data['user']
        player_level = user.current_level
        
        score_result = calculate_final_score(base_score, player_level)
        
        boss = form.save(commit=False)
        boss.final_score = score_result['final_score']
        boss.bonus_applied = score_result['bonus_applied']
        boss.save()
        
        messages.success(
            self.request, 
            f'Boss battle "{form.cleaned_data["name"]}" berhasil diupdate! '
            f'Final Score: {boss.final_score} (Base: {base_score} + Bonus: {boss.bonus_applied})'
        )
        return redirect(self.success_url)


@login_required
def boss_delete(request, pk):
    """Delete view untuk menghapus boss battle"""
    if not request.user.is_admin():
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus boss battle.')
        return redirect('admin_dashboard:boss_list')
    
    boss = get_object_or_404(Boss, pk=pk)
    
    if request.method == 'POST':
        boss_name = boss.name
        boss.delete()
        messages.success(request, f'Boss battle "{boss_name}" berhasil dihapus!')
        return redirect('admin_dashboard:boss_list')
    
    return render(request, 'admin/boss_confirm_delete.html', {'boss': boss})


# Punishment Views for Admin
class PunishmentListView(ListView):
    """List view untuk semua punishments (Admin) dengan query optimization"""
    model = Punishment
    template_name = 'admin/punishment_list.html'
    context_object_name = 'punishments'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Optimize query dengan select_related"""
        return Punishment.objects.select_related('user', 'created_by').all()


class PunishmentCreateView(CreateView):
    """Create view untuk membuat punishment baru"""
    model = Punishment
    form_class = PunishmentForm
    template_name = 'admin/punishment_form.html'
    success_url = reverse_lazy('admin_dashboard:punishment_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        with transaction.atomic():
            punishment = form.save(commit=False)
            punishment.created_by = self.request.user
            
            # Jika type adalah plagiarism atau cheating, gunakan PunishmentService
            if punishment.type == 'plagiarism':
                # Gunakan PunishmentService untuk plagiarism
                severity = punishment.severity
                evidence = punishment.evidence if punishment.evidence else None
                PunishmentService.apply_plagiarism_punishment(
                    user=punishment.user,
                    severity=severity,
                    evidence=evidence,
                    created_by=self.request.user
                )
                
                # Send notification
                try:
                    from core.notifications import send_punishment_notification
                    send_punishment_notification(
                        user_id=punishment.user.id,
                        punishment_type='Plagiarism',
                        severity=severity.title(),
                        exp_penalty=PLAGIARISM_RULES[severity]['exp_penalty']
                    )
                except Exception as e:
                    pass
                
                messages.success(
                    self.request, 
                    f'Plagiarism punishment untuk {punishment.user.username} berhasil diterapkan!'
                )
            elif punishment.type == 'cheating':
                # Untuk cheating, perlu boss_type dari evidence atau form
                boss_type = punishment.evidence.get('boss_type', 'mini_boss') if punishment.evidence else 'mini_boss'
                PunishmentService.apply_cheating_punishment(
                    user=punishment.user,
                    boss_type=boss_type,
                    created_by=self.request.user
                )
                messages.success(
                    self.request, 
                    f'Cheating punishment untuk {punishment.user.username} berhasil diterapkan!'
                )
            else:
                # Untuk type lain (late_submission, absence), gunakan method biasa
                punishment.save()
                punishment.apply_punishment()
                
                # Send notification
                try:
                    from core.notifications import send_punishment_notification
                    send_punishment_notification(
                        user_id=punishment.user.id,
                        punishment_type=punishment.get_type_display(),
                        severity=punishment.get_severity_display(),
                        exp_penalty=punishment.exp_penalty
                    )
                except Exception as e:
                    pass
                
                messages.success(
                    self.request, 
                    f'Punishment untuk {punishment.user.username} berhasil dibuat!'
                )
        return redirect(self.success_url)


class PunishmentUpdateView(UpdateView):
    """Update view untuk mengedit punishment"""
    model = Punishment
    form_class = PunishmentForm
    template_name = 'admin/punishment_form.html'
    success_url = reverse_lazy('admin_dashboard:punishment_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        messages.success(
            self.request, 
            f'Punishment berhasil diupdate!'
        )
        return super().form_valid(form)


@login_required
def punishment_delete(request, pk):
    """Delete view untuk menghapus punishment"""
    if not request.user.is_admin():
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus punishment.')
        return redirect('admin_dashboard:punishment_list')
    
    punishment = get_object_or_404(Punishment, pk=pk)
    
    if request.method == 'POST':
        punishment_user = punishment.user.username
        punishment.delete()
        messages.success(request, f'Punishment untuk {punishment_user} berhasil dihapus!')
        return redirect('admin_dashboard:punishment_list')
    
    return render(request, 'admin/punishment_confirm_delete.html', {'punishment': punishment})


@login_required
def resolve_punishment(request, pk):
    """View untuk resolve punishment"""
    if not request.user.is_admin():
        messages.error(request, 'Anda tidak memiliki akses untuk resolve punishment.')
        return redirect('admin_dashboard:punishment_list')
    
    punishment = get_object_or_404(Punishment, pk=pk)
    
    if request.method == 'POST':
        with transaction.atomic():
            punishment.resolved = True
            punishment.resolved_at = timezone.now()
            punishment.save()
            
            # Deactivate related status effects
            StatusEffect.objects.filter(
                user=punishment.user,
                is_active=True,
                description__startswith=f"Punishment effect: {punishment.description}"
            ).update(is_active=False)
            
            messages.success(request, f'Punishment untuk {punishment.user.username} berhasil di-resolve!')
            return redirect('admin_dashboard:punishment_list')
    
    return render(request, 'admin/punishment_resolve.html', {'punishment': punishment})


class StatusEffectListView(ListView):
    """List view untuk semua status effects (Admin)"""
    model = StatusEffect
    template_name = 'admin/status_effect_list.html'
    context_object_name = 'status_effects'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)


# Analytics & Reporting Views
@login_required
def analytics_dashboard(request):
    """Analytics dashboard untuk admin dengan metrics dan charts"""
    if not request.user.is_admin():
        return redirect('player:dashboard')
    
    # Time ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Player Engagement Metrics
    total_players = User.objects.filter(role='player').count()
    active_players_week = User.objects.filter(
        role='player',
        exp_logs__created_at__gte=week_ago
    ).distinct().count()
    active_players_month = User.objects.filter(
        role='player',
        exp_logs__created_at__gte=month_ago
    ).distinct().count()
    
    # EXP Distribution
    exp_distribution = User.objects.filter(role='player').values('current_level').annotate(
        count=Count('id')
    ).order_by('current_level')
    
    # Activity Statistics
    activity_stats = ExpLog.objects.values('activity_type').annotate(
        total=Sum('exp_earned'),
        count=Count('id')
    ).order_by('-total')
    
    # Achievement Completion Rates (simplified)
    level_5_plus = User.objects.filter(role='player', current_level__gte=5).count()
    level_10_plus = User.objects.filter(role='player', current_level__gte=10).count()
    high_honor = User.objects.filter(role='player', honor_points__gte=800).count()
    
    # Punishment Statistics
    total_punishments = Punishment.objects.count()
    active_punishments = Punishment.objects.filter(resolved=False).count()
    resolved_punishments = Punishment.objects.filter(resolved=True).count()
    punishment_by_type = Punishment.objects.values('type').annotate(
        count=Count('id')
    )
    punishment_by_severity = Punishment.objects.values('severity').annotate(
        count=Count('id')
    )
    
    # EXP Growth Over Time (last 30 days)
    exp_growth_data = ExpLog.objects.filter(
        created_at__gte=month_ago
    ).extra(
        select={'day': "DATE(created_at)"}
    ).values('day').annotate(
        total_exp=Sum('exp_earned'),
        count=Count('id')
    ).order_by('day')
    
    # Top Players
    top_players = User.objects.filter(role='player').order_by('-total_exp', '-current_level')[:10]
    
    # Sidequest Statistics
    total_sidequests = Sidequest.objects.count()
    active_sidequests = Sidequest.objects.filter(status='active').count()
    total_submissions = SidequestSubmission.objects.count()
    graded_submissions = SidequestSubmission.objects.filter(grade__isnull=False).count()
    
    # Dungeon Statistics
    total_dungeons = Dungeon.objects.count()
    active_dungeons = Dungeon.objects.filter(status='active').count()
    total_attendances = Attendance.objects.filter(attended=True).count()
    
    # Format data for charts
    exp_growth_chart = []
    for item in exp_growth_data:
        exp_growth_chart.append({
            'day': item['day'].strftime('%Y-%m-%d') if hasattr(item['day'], 'strftime') else str(item['day']),
            'total_exp': item['total_exp'] or 0,
            'count': item['count']
        })
    
    context = {
        'total_players': total_players,
        'active_players_week': active_players_week,
        'active_players_month': active_players_month,
        'exp_distribution': list(exp_distribution),
        'activity_stats': list(activity_stats),
        'level_5_plus': level_5_plus,
        'level_10_plus': level_10_plus,
        'high_honor': high_honor,
        'total_punishments': total_punishments,
        'active_punishments': active_punishments,
        'resolved_punishments': resolved_punishments,
        'punishment_by_type': list(punishment_by_type),
        'punishment_by_severity': list(punishment_by_severity),
        'exp_growth_data': exp_growth_chart,
        'top_players': top_players,
        'total_sidequests': total_sidequests,
        'active_sidequests': active_sidequests,
        'total_submissions': total_submissions,
        'graded_submissions': graded_submissions,
        'total_dungeons': total_dungeons,
        'active_dungeons': active_dungeons,
        'total_attendances': total_attendances,
    }
    
    return render(request, 'admin/analytics_dashboard.html', context)


@login_required
def export_player_progress_csv(request):
    """Export player progress to CSV"""
    if not request.user.is_admin():
        return HttpResponse('Unauthorized', status=403)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="player_progress_{}.csv"'.format(
        timezone.now().strftime('%Y%m%d')
    )
    
    writer = csv.writer(response)
    writer.writerow([
        'Username', 'Email', 'Level', 'Current EXP', 'Total EXP', 
        'Honor Points', 'Dungeons Attended', 'Sidequests Submitted', 
        'Boss Battles', 'Punishments', 'Last Activity'
    ])
    
    players = User.objects.filter(role='player').annotate(
        dungeons_attended=Count('attendances', filter=Q(attendances__attended=True)),
        sidequests_submitted=Count('sidequest_submissions'),
        boss_battles=Count('boss_battles'),
        punishments_count=Count('punishments'),
        last_activity=Max('exp_logs__created_at')
    )
    
    for player in players:
        writer.writerow([
            player.username,
            player.email or '',
            player.current_level,
            player.current_exp,
            player.total_exp,
            player.honor_points,
            player.dungeons_attended or 0,
            player.sidequests_submitted or 0,
            player.boss_battles or 0,
            player.punishments_count or 0,
            player.last_activity.strftime('%Y-%m-%d %H:%M:%S') if player.last_activity else ''
        ])
    
    return response


@login_required
def export_grades_pdf(request):
    """Export grades to PDF (simplified - returns HTML that can be printed as PDF)"""
    if not request.user.is_admin():
        return HttpResponse('Unauthorized', status=403)
    
    # Get all graded submissions
    submissions = SidequestSubmission.objects.filter(
        grade__isnull=False
    ).select_related('user', 'sidequest').order_by('-submitted_at')
    
    context = {
        'submissions': submissions,
        'export_date': timezone.now(),
    }
    
    return render(request, 'admin/grades_pdf.html', context)


@login_required
def export_analytics_excel(request):
    """Export analytics data to Excel (CSV format for simplicity)"""
    if not request.user.is_admin():
        return HttpResponse('Unauthorized', status=403)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="analytics_{}.csv"'.format(
        timezone.now().strftime('%Y%m%d')
    )
    
    writer = csv.writer(response)
    
    # Summary Sheet
    writer.writerow(['Analytics Report', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Players', User.objects.filter(role='player').count()])
    writer.writerow(['Total EXP Earned', ExpLog.objects.aggregate(Sum('exp_earned'))['exp_earned__sum'] or 0])
    writer.writerow(['Total Dungeons', Dungeon.objects.count()])
    writer.writerow(['Total Sidequests', Sidequest.objects.count()])
    writer.writerow(['Total Punishments', Punishment.objects.count()])
    writer.writerow([])
    
    # EXP Distribution
    writer.writerow(['EXP Distribution by Level'])
    writer.writerow(['Level', 'Player Count'])
    exp_dist = User.objects.filter(role='player').values('current_level').annotate(
        count=Count('id')
    ).order_by('current_level')
    for item in exp_dist:
        writer.writerow([item['current_level'], item['count']])
    writer.writerow([])
    
    # Activity Statistics
    writer.writerow(['Activity Statistics'])
    writer.writerow(['Activity Type', 'Total EXP', 'Count'])
    activity_stats = ExpLog.objects.values('activity_type').annotate(
        total=Sum('exp_earned'),
        count=Count('id')
    )
    for item in activity_stats:
        writer.writerow([
            item['activity_type'],
            item['total'] or 0,
            item['count']
        ])
    
    return response
