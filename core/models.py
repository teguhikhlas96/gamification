from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User


class Level(models.Model):
    """
    Model untuk menyimpan informasi level dan EXP yang dibutuhkan
    """
    level = models.IntegerField(unique=True, help_text="Level number")
    exp_required = models.IntegerField(help_text="Total EXP required to reach this level")
    bonus_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of bonus or reward for reaching this level"
    )
    
    class Meta:
        ordering = ['level']
        verbose_name = 'Level'
        verbose_name_plural = 'Levels'
    
    def __str__(self):
        return f"Level {self.level} ({self.exp_required} EXP)"
    
    def get_absolute_url(self):
        return reverse('core:level_detail', kwargs={'pk': self.pk})


class ExpLog(models.Model):
    """
    Model untuk tracking EXP yang diperoleh user dari berbagai aktivitas
    """
    ACTIVITY_TYPES = [
        ('quest', 'Quest'),
        ('assignment', 'Assignment'),
        ('participation', 'Participation'),
        ('bonus', 'Bonus'),
        ('admin', 'Admin Grant'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exp_logs'
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES,
        default='other'
    )
    exp_earned = models.IntegerField(help_text="Amount of EXP earned")
    description = models.TextField(help_text="Description of the activity")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'EXP Log'
        verbose_name_plural = 'EXP Logs'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()} (+{self.exp_earned} EXP)"


class Dungeon(models.Model):
    """
    Model untuk pertemuan kelas (Dungeon)
    """
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=200, help_text="Nama pertemuan kelas")
    description = models.TextField(help_text="Deskripsi pertemuan")
    scheduled_date = models.DateTimeField(help_text="Tanggal dan waktu pertemuan")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned'
    )
    exp_reward = models.IntegerField(
        default=50,
        help_text="EXP yang diberikan untuk kehadiran"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
        verbose_name = 'Dungeon'
        verbose_name_plural = 'Dungeons'
        indexes = [
            models.Index(fields=['status', '-scheduled_date']),
            models.Index(fields=['scheduled_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    def get_absolute_url(self):
        return reverse('admin_dashboard:dungeon_list')
    
    def get_attended_count(self):
        """Get count of players who attended"""
        return self.attendances.filter(attended=True).count()


class Attendance(models.Model):
    """
    Model untuk tracking kehadiran user di dungeon
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    dungeon = models.ForeignKey(
        Dungeon,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    attended = models.BooleanField(
        default=False,
        help_text="Apakah user hadir"
    )
    participation_exp = models.IntegerField(
        default=0,
        help_text="EXP yang diperoleh dari kehadiran"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendances'
        unique_together = ['user', 'dungeon']  # Satu user hanya bisa satu attendance per dungeon
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['dungeon', 'attended']),
            models.Index(fields=['attended', '-created_at']),
        ]
    
    def __str__(self):
        status = "Attended" if self.attended else "Absent"
        return f"{self.user.username} - {self.dungeon.name} ({status})"


class Sidequest(models.Model):
    """
    Model untuk tugas/sidequest
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]
    
    title = models.CharField(max_length=200, help_text="Judul tugas")
    description = models.TextField(help_text="Deskripsi tugas")
    instructions = models.TextField(help_text="Instruksi pengerjaan tugas")
    due_date = models.DateTimeField(help_text="Batas waktu pengumpulan")
    exp_reward = models.IntegerField(
        default=200,
        help_text="EXP yang diberikan untuk submission tepat waktu"
    )
    late_exp_reward = models.IntegerField(
        default=100,
        help_text="EXP yang diberikan untuk submission terlambat"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-due_date']
        verbose_name = 'Sidequest'
        verbose_name_plural = 'Sidequests'
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def get_absolute_url(self):
        return reverse('admin_dashboard:sidequest_list')
    
    def is_overdue(self):
        """Check jika due date sudah lewat"""
        from django.utils import timezone
        return timezone.now() > self.due_date
    
    def get_submission_count(self):
        """Get jumlah submission"""
        return self.submissions.count()
    
    def get_graded_count(self):
        """Get jumlah submission yang sudah dinilai"""
        return self.submissions.exclude(grade__isnull=True).count()


class SidequestSubmission(models.Model):
    """
    Model untuk submission tugas oleh player
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sidequest_submissions'
    )
    sidequest = models.ForeignKey(
        Sidequest,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    submitted_file = models.FileField(
        upload_to='submissions/%Y/%m/%d/',
        help_text="File yang dikumpulkan"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nilai yang diberikan (0-100)"
    )
    exp_earned = models.IntegerField(
        default=0,
        help_text="EXP yang diperoleh dari submission"
    )
    feedback = models.TextField(
        blank=True,
        null=True,
        help_text="Feedback dari admin"
    )
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Sidequest Submission'
        verbose_name_plural = 'Sidequest Submissions'
        unique_together = ['user', 'sidequest']  # Satu user hanya bisa submit sekali per sidequest
        indexes = [
            models.Index(fields=['user', '-submitted_at']),
            models.Index(fields=['sidequest', '-submitted_at']),
            models.Index(fields=['grade', '-submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.sidequest.title}"
    
    def is_late(self):
        """Check jika submission terlambat"""
        return self.submitted_at > self.sidequest.due_date
    
    def get_exp_reward(self):
        """Get EXP reward berdasarkan apakah terlambat atau tidak"""
        if self.is_late():
            return self.sidequest.late_exp_reward
        return self.sidequest.exp_reward


class Boss(models.Model):
    """
    Model untuk Boss Battle (ujian)
    """
    TYPE_CHOICES = [
        ('mini_boss', 'Mini Boss'),
        ('mid_boss', 'Mid Boss'),
        ('last_boss', 'Last Boss'),
    ]
    
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        help_text="Tipe boss battle"
    )
    name = models.CharField(max_length=200, help_text="Nama boss/ujian")
    description = models.TextField(help_text="Deskripsi boss battle")
    base_score = models.IntegerField(
        help_text="Nilai asli (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    final_score = models.IntegerField(
        help_text="Nilai akhir setelah bonus (auto-calculated)",
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='boss_battles',
        help_text="Player yang melakukan battle"
    )
    battle_date = models.DateField(help_text="Tanggal battle/ujian")
    bonus_applied = models.IntegerField(
        default=0,
        help_text="Bonus yang diterapkan berdasarkan level"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-battle_date']
        verbose_name = 'Boss'
        verbose_name_plural = 'Bosses'
        indexes = [
            models.Index(fields=['user', '-battle_date']),
            models.Index(fields=['type', '-battle_date']),
            models.Index(fields=['battle_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.get_type_display()})"
    
    def get_absolute_url(self):
        return reverse('admin_dashboard:boss_list')


class Punishment(models.Model):
    """
    Model untuk punishment/hukuman yang diberikan ke player
    """
    TYPE_CHOICES = [
        ('plagiarism', 'Plagiarism'),
        ('cheating', 'Cheating'),
        ('late_submission', 'Late Submission'),
        ('absence', 'Absence'),
    ]
    
    SEVERITY_CHOICES = [
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='punishments',
        help_text="Player yang dihukum"
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        help_text="Tipe punishment"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        help_text="Tingkat keparahan"
    )
    description = models.TextField(help_text="Deskripsi punishment")
    exp_penalty = models.IntegerField(
        default=0,
        help_text="EXP yang dikurangi (penalty)"
    )
    status_effect = models.CharField(
        max_length=20,
        choices=[
            ('curse', 'Curse'),
            ('weakness', 'Weakness'),
            ('silence', 'Silence'),
            ('fatigue', 'Fatigue'),
        ],
        blank=True,
        null=True,
        help_text="Status effect yang diterapkan (optional)"
    )
    duration_days = models.IntegerField(
        default=0,
        help_text="Durasi punishment dalam hari"
    )
    resolved = models.BooleanField(
        default=False,
        help_text="Apakah punishment sudah diselesaikan"
    )
    evidence = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Bukti atau data tambahan (JSON)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='punishments_created',
        help_text="Admin yang membuat punishment"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Punishment'
        verbose_name_plural = 'Punishments'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['type', 'resolved']),
            models.Index(fields=['resolved', '-created_at']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_type_display()} ({self.get_severity_display()})"
    
    def get_absolute_url(self):
        return reverse('admin_dashboard:punishment_list')
    
    def apply_punishment(self):
        """Menerapkan punishment ke user"""
        from django.utils import timezone
        from core.services import add_exp
        
        # Kurangi EXP
        if self.exp_penalty > 0:
            add_exp(
                user=self.user,
                amount=-self.exp_penalty,
                activity_type='other',
                description=f"Punishment penalty: {self.get_type_display()}"
            )
        
        # Apply status effect jika ada
        if self.status_effect:
            # Set exp_multiplier berdasarkan effect type
            exp_multiplier_map = {
                'curse': 0.5,      # 50% EXP
                'weakness': 0.75,   # 75% EXP
                'silence': 0.9,     # 90% EXP
                'fatigue': 0.8,     # 80% EXP
            }
            exp_multiplier = exp_multiplier_map.get(self.status_effect, 1.0)
            
            StatusEffect.objects.create(
                user=self.user,
                effect_type=self.status_effect,
                description=f"Punishment effect: {self.description}",
                exp_multiplier=exp_multiplier,
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=self.duration_days) if self.duration_days > 0 else None,
                is_active=True
            )


class StatusEffect(models.Model):
    """
    Model untuk status effect yang diterapkan ke user
    """
    EFFECT_TYPE_CHOICES = [
        ('curse', 'Curse'),
        ('weakness', 'Weakness'),
        ('silence', 'Silence'),
        ('fatigue', 'Fatigue'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='status_effects',
        help_text="Player yang terkena effect"
    )
    effect_type = models.CharField(
        max_length=20,
        choices=EFFECT_TYPE_CHOICES,
        help_text="Tipe status effect"
    )
    description = models.TextField(help_text="Deskripsi effect")
    exp_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.0,
        help_text="Multiplier untuk EXP (1.0 = normal, <1.0 = reduced, >1.0 = bonus)"
    )
    blocks_activities = models.JSONField(
        default=list,
        blank=True,
        help_text="Aktivitas yang diblokir (list of activity types)"
    )
    start_date = models.DateTimeField(help_text="Tanggal mulai effect")
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Tanggal berakhir effect (null = permanent until resolved)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Apakah effect masih aktif"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Status Effect'
        verbose_name_plural = 'Status Effects'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['is_active', '-start_date']),
            models.Index(fields=['effect_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_effect_type_display()}"
    
    def get_absolute_url(self):
        return reverse('admin_dashboard:status_effect_list')
    
    def is_expired(self):
        """Check jika effect sudah expired"""
        from django.utils import timezone
        if self.end_date is None:
            return False
        return timezone.now() > self.end_date
    
    def deactivate(self):
        """Deactivate effect"""
        self.is_active = False
        self.save()
