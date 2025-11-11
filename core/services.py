from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from accounts.models import User
from .models import Level, ExpLog, Punishment, StatusEffect


def add_exp(user, amount, activity_type='other', description=''):
    """
    Menambahkan EXP ke user dan mencatatnya di ExpLog
    Mempertimbangkan status effects (exp_multiplier)
    
    Args:
        user: User instance
        amount: Jumlah EXP yang ditambahkan
        activity_type: Tipe aktivitas (quest, assignment, participation, bonus, admin, other)
        description: Deskripsi aktivitas
    
    Returns:
        dict: {
            'success': bool,
            'new_exp': int,
            'new_total_exp': int,
            'level_up': bool,
            'new_level': int or None,
            'exp_multiplier': float,
            'original_amount': int,
            'actual_amount': int
        }
    """
    with transaction.atomic():
        # Check active status effects
        active_effects = StatusEffect.objects.filter(
            user=user,
            is_active=True
        )
        
        # Calculate exp multiplier (multiply all active effects)
        exp_multiplier = 1.0
        for effect in active_effects:
            if effect.is_expired():
                effect.deactivate()
            else:
                exp_multiplier *= float(effect.exp_multiplier)
        
        # Apply honor points bonus/penalty (import di sini untuk avoid circular import)
        honor_privileges = check_honor_privileges(user)
        exp_multiplier *= honor_privileges['exp_multiplier_bonus']
        
        # Calculate actual EXP dengan multiplier
        original_amount = amount
        actual_amount = int(amount * exp_multiplier)
        
        # Update user EXP
        user.current_exp += actual_amount
        user.total_exp += actual_amount
        
        # Simpan perubahan
        user.save()
        
        # Catat di ExpLog dengan actual amount
        ExpLog.objects.create(
            user=user,
            activity_type=activity_type,
            exp_earned=actual_amount,
            description=description + (f" (Multiplier: {exp_multiplier:.2f}x)" if exp_multiplier != 1.0 else "")
        )
        
        # Check level up
        level_up_result = check_level_up(user)
        
        # Jika level up, apply bonus
        if level_up_result.get('level_up'):
            new_level = level_up_result.get('new_level')
            old_level = level_up_result.get('old_level')
            
            # Apply bonus
            bonus = apply_level_bonus(user, new_level)
            
            # Log level up activity
            ExpLog.objects.create(
                user=user,
                activity_type='bonus',
                exp_earned=0,
                description=f"Level Up! {old_level} → {new_level}. Bonus: {bonus['honor_points']} Honor Points"
            )
            
            # Send real-time notification
            try:
                from core.notifications import send_level_up_notification, broadcast_leaderboard_update
                send_level_up_notification(
                    user_id=user.id,
                    old_level=old_level,
                    new_level=new_level,
                    honor_points_bonus=bonus.get('honor_points', 0)
                )
                # Broadcast leaderboard update
                broadcast_leaderboard_update()
            except Exception as e:
                # Silently fail if notification system is not available
                pass
        
        return {
            'success': True,
            'new_exp': user.current_exp,
            'new_total_exp': user.total_exp,
            'level_up': level_up_result.get('level_up', False),
            'new_level': level_up_result.get('new_level'),
            'old_level': level_up_result.get('old_level'),
            'exp_multiplier': exp_multiplier,
            'original_amount': original_amount,
            'actual_amount': actual_amount,
            'exp_log': ExpLog.objects.filter(user=user).latest('created_at')
        }


def check_level_up(user):
    """
    Mengecek apakah user bisa naik level berdasarkan total_exp
    
    Args:
        user: User instance
    
    Returns:
        dict: {
            'level_up': bool,
            'new_level': int or None,
            'exp_remaining': int
        }
    """
    # Refresh user dari database untuk mendapatkan data terbaru
    user.refresh_from_db()
    
    # Get level berdasarkan total_exp
    level = Level.objects.filter(exp_required__lte=user.total_exp).order_by('-level').first()
    
    if level and level.level > user.current_level:
        old_level = user.current_level
        user.current_level = level.level
        
        # Calculate remaining EXP for current level
        # EXP yang sudah digunakan untuk mencapai level ini
        exp_used = level.exp_required
        
        # EXP yang tersisa untuk level berikutnya
        exp_remaining = user.total_exp - exp_used
        
        # Update current_exp (EXP yang tersisa untuk level berikutnya)
        user.current_exp = max(0, exp_remaining)  # Pastikan tidak negatif
        user.save()
        
        return {
            'level_up': True,
            'old_level': old_level,
            'new_level': level.level,
            'exp_remaining': exp_remaining,
            'bonus': calculate_bonus(level.level)
        }
    
    # Calculate remaining EXP untuk level berikutnya
    current_level_obj = Level.objects.filter(level=user.current_level).first()
    if current_level_obj:
        exp_used = current_level_obj.exp_required
        exp_remaining = user.total_exp - exp_used
    else:
        exp_remaining = user.total_exp
    
    return {
        'level_up': False,
        'current_level': user.current_level,
        'exp_remaining': max(0, exp_remaining)
    }


def calculate_bonus(level):
    """
    Menghitung bonus yang didapat user ketika mencapai level tertentu
    
    Args:
        level: Level number (int)
    
    Returns:
        dict: {
            'honor_points': int,
            'description': str
        }
    """
    level_obj = Level.objects.filter(level=level).first()
    
    if not level_obj:
        return {
            'honor_points': 0,
            'description': 'No bonus available'
        }
    
    # Bonus honor points berdasarkan level
    # Level 1-5: 10 points per level
    # Level 6-10: 20 points per level
    # Level 11+: 30 points per level
    if level <= 5:
        honor_points = level * 10
    elif level <= 10:
        honor_points = 50 + (level - 5) * 20
    else:
        honor_points = 150 + (level - 10) * 30
    
    description = level_obj.bonus_description or f"Reached Level {level}!"
    
    return {
        'honor_points': honor_points,
        'description': description
    }


def apply_level_bonus(user, level):
    """
    Menerapkan bonus honor points ketika user naik level
    
    Args:
        user: User instance
        level: Level number (int)
    """
    bonus = calculate_bonus(level)
    user.honor_points += bonus['honor_points']
    user.save()
    
    return bonus


# Boss Battle Services
def apply_bonus_rules(level):
    """
    Menerapkan bonus rules berdasarkan level player
    
    Args:
        level: Level player (int)
    
    Returns:
        int: Bonus points yang diterapkan
    """
    if level <= 5:
        return 0  # No bonus
    elif level <= 10:
        return 5  # +5 points
    elif level <= 15:
        return 10  # +10 points
    else:
        # Level 16+: +15 points (optional, bisa disesuaikan)
        return 15


def calculate_final_score(base_score, player_level):
    """
    Menghitung final score dengan bonus berdasarkan level
    
    Args:
        base_score: Nilai asli (0-100)
        player_level: Level player (int)
    
    Returns:
        dict: {
            'final_score': int,
            'bonus_applied': int,
            'base_score': int
        }
    """
    bonus = apply_bonus_rules(player_level)
    final_score = min(100, base_score + bonus)  # Maksimal 100
    
    return {
        'final_score': final_score,
        'bonus_applied': bonus,
        'base_score': base_score
    }


# Punishment Rules Configuration
PLAGIARISM_RULES = {
    'minor': {
        'exp_penalty': 100,
        'honor_loss': 10,
        'status_effect': None,
        'duration': 0
    },
    'major': {
        'exp_penalty': 300,
        'honor_loss': 20,
        'status_effect': 'curse',
        'duration': 7
    },
    'critical': {
        'exp_penalty': 500,
        'honor_loss': 30,
        'status_effect': 'curse',
        'duration': 14
    }
}

CHEATING_RULES = {
    'mini_boss': {
        'exp_penalty': 200,
        'honor_loss': 15,
        'status_effect': 'weakness',
        'duration': 5
    },
    'mid_boss': {
        'exp_penalty': 400,
        'honor_loss': 25,
        'status_effect': 'curse',
        'duration': 10
    },
    'last_boss': {
        'exp_penalty': 600,
        'honor_loss': 40,
        'status_effect': 'curse',
        'duration': 21
    }
}

ABSENCE_RULES = {
    'threshold': 3,  # Jumlah absen berturut-turut untuk trigger punishment
    'exp_penalty': 50,
    'honor_loss': 5,
    'status_effect': 'fatigue',
    'duration': 3
}


class PunishmentService:
    """
    Service class untuk mengelola punishment rules dan aplikasinya
    """
    
    @staticmethod
    def apply_plagiarism_punishment(user, severity, evidence=None, created_by=None):
        """
        Menerapkan punishment untuk plagiarism
        
        Args:
            user: User instance
            severity: 'minor', 'major', atau 'critical'
            evidence: Dict evidence (optional)
            created_by: Admin yang membuat punishment
        
        Returns:
            Punishment instance
        """
        if severity not in PLAGIARISM_RULES:
            raise ValueError(f"Invalid severity: {severity}")
        
        rules = PLAGIARISM_RULES[severity]
        
        with transaction.atomic():
            # Create punishment
            punishment = Punishment.objects.create(
                user=user,
                type='plagiarism',
                severity=severity,
                description=f"Plagiarism detected - {severity} severity",
                exp_penalty=rules['exp_penalty'],
                status_effect=rules.get('status_effect'),
                duration_days=rules.get('duration', 0),
                evidence=evidence or {},
                created_by=created_by
            )
            
            # Apply punishment
            punishment.apply_punishment()
            
            # Decrease honor points
            if rules.get('honor_loss', 0) > 0:
                user.honor_points = max(0, user.honor_points - rules['honor_loss'])
                user.save()
            
            return punishment
    
    @staticmethod
    def apply_cheating_punishment(user, boss_type, created_by=None):
        """
        Menerapkan punishment untuk cheating di boss battle
        
        Args:
            user: User instance
            boss_type: 'mini_boss', 'mid_boss', atau 'last_boss'
            created_by: Admin yang membuat punishment
        
        Returns:
            Punishment instance
        """
        if boss_type not in CHEATING_RULES:
            raise ValueError(f"Invalid boss_type: {boss_type}")
        
        rules = CHEATING_RULES[boss_type]
        
        with transaction.atomic():
            # Create punishment
            punishment = Punishment.objects.create(
                user=user,
                type='cheating',
                severity='major' if boss_type == 'last_boss' else 'minor',
                description=f"Cheating detected in {boss_type.replace('_', ' ').title()} battle",
                exp_penalty=rules['exp_penalty'],
                status_effect=rules.get('status_effect'),
                duration_days=rules.get('duration', 0),
                evidence={'boss_type': boss_type},
                created_by=created_by
            )
            
            # Apply punishment
            punishment.apply_punishment()
            
            # Decrease honor points
            if rules.get('honor_loss', 0) > 0:
                user.honor_points = max(0, user.honor_points - rules['honor_loss'])
                user.save()
            
            return punishment
    
    @staticmethod
    def check_and_apply_absence_punishment(user, created_by=None):
        """
        Check dan terapkan punishment untuk absence berturut-turut
        
        Args:
            user: User instance
            created_by: Admin yang membuat punishment
        
        Returns:
            Punishment instance or None
        """
        from .models import Attendance
        
        # Get recent absences (last 5 dungeons)
        recent_attendances = Attendance.objects.filter(
            user=user
        ).order_by('-created_at')[:ABSENCE_RULES['threshold']]
        
        # Check jika semua adalah absence
        consecutive_absences = 0
        for attendance in recent_attendances:
            if not attendance.attended:
                consecutive_absences += 1
            else:
                break
        
        # Jika mencapai threshold, apply punishment
        if consecutive_absences >= ABSENCE_RULES['threshold']:
            rules = ABSENCE_RULES
            
            with transaction.atomic():
                # Check jika sudah ada punishment untuk absence yang belum resolved
                existing = Punishment.objects.filter(
                    user=user,
                    type='absence',
                    resolved=False
                ).first()
                
                if existing:
                    return existing  # Jangan duplicate punishment
                
                # Create punishment
                punishment = Punishment.objects.create(
                    user=user,
                    type='absence',
                    severity='minor',
                    description=f"Consecutive absence detected ({consecutive_absences} times)",
                    exp_penalty=rules['exp_penalty'],
                    status_effect=rules.get('status_effect'),
                    duration_days=rules.get('duration', 0),
                    evidence={'consecutive_absences': consecutive_absences},
                    created_by=created_by
                )
                
                # Apply punishment
                punishment.apply_punishment()
                
                # Decrease honor points
                if rules.get('honor_loss', 0) > 0:
                    user.honor_points = max(0, user.honor_points - rules['honor_loss'])
                    user.save()
                
                return punishment
        
        return None
    
    @staticmethod
    def recover_honor_points(user, amount=1):
        """
        Recover honor points secara gradual (dipanggil secara berkala)
        
        Args:
            user: User instance
            amount: Jumlah honor points yang di-recover (default 1)
        
        Returns:
            bool: True jika honor points berhasil di-recover
        """
        # Maximum honor points (bisa disesuaikan)
        max_honor = 1000
        
        if user.honor_points < max_honor:
            old_honor = user.honor_points
            user.honor_points = min(max_honor, user.honor_points + amount)
            user.save()
            return True
        return False


def check_honor_privileges(user):
    """
    Check game privileges berdasarkan honor points
    
    Args:
        user: User instance
    
    Returns:
        dict: {
            'can_submit_sidequest': bool,
            'can_join_dungeon': bool,
            'can_participate_boss': bool,
            'exp_multiplier_bonus': float,
            'honor_tier': str
        }
    """
    honor = user.honor_points
    
    # Honor tiers
    if honor >= 800:
        tier = 'exalted'
        can_submit = True
        can_join = True
        can_boss = True
        exp_bonus = 1.2  # 20% bonus
    elif honor >= 600:
        tier = 'honored'
        can_submit = True
        can_join = True
        can_boss = True
        exp_bonus = 1.1  # 10% bonus
    elif honor >= 400:
        tier = 'respected'
        can_submit = True
        can_join = True
        can_boss = True
        exp_bonus = 1.0  # No bonus
    elif honor >= 200:
        tier = 'neutral'
        can_submit = True
        can_join = True
        can_boss = True
        exp_bonus = 0.95  # 5% penalty
    elif honor >= 100:
        tier = 'disgraced'
        can_submit = True
        can_join = True
        can_boss = False  # Tidak bisa ikut boss battle
        exp_bonus = 0.9  # 10% penalty
    elif honor >= 50:
        tier = 'shamed'
        can_submit = True
        can_join = False  # Tidak bisa ikut dungeon
        can_boss = False
        exp_bonus = 0.8  # 20% penalty
    else:
        tier = 'outcast'
        can_submit = False  # Tidak bisa submit sidequest
        can_join = False
        can_boss = False
        exp_bonus = 0.5  # 50% penalty
    
    return {
        'can_submit_sidequest': can_submit,
        'can_join_dungeon': can_join,
        'can_participate_boss': can_boss,
        'exp_multiplier_bonus': exp_bonus,
        'honor_tier': tier,
        'honor_points': honor
    }

