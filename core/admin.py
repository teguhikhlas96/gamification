from django.contrib import admin
from django.db.models import Count, Sum, Q
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import Level, ExpLog, Dungeon, Attendance, Sidequest, SidequestSubmission, Boss, Punishment, StatusEffect
from accounts.models import User


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('level', 'exp_required', 'bonus_description_preview')
    list_filter = ('level',)
    search_fields = ('level', 'bonus_description')
    ordering = ('level',)
    
    def bonus_description_preview(self, obj):
        """Preview bonus description (truncated)"""
        if obj.bonus_description:
            return obj.bonus_description[:50] + '...' if len(obj.bonus_description) > 50 else obj.bonus_description
        return '-'
    bonus_description_preview.short_description = 'Bonus Description'


# Custom Filters
class ExpEarnedFilter(admin.SimpleListFilter):
    title = 'EXP Earned'
    parameter_name = 'exp_earned'
    
    def lookups(self, request, model_admin):
        return (
            ('positive', 'Positive EXP'),
            ('negative', 'Negative EXP'),
            ('zero', 'Zero EXP'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'positive':
            return queryset.filter(exp_earned__gt=0)
        if self.value() == 'negative':
            return queryset.filter(exp_earned__lt=0)
        if self.value() == 'zero':
            return queryset.filter(exp_earned=0)


class LevelRangeFilter(admin.SimpleListFilter):
    title = 'Level Range'
    parameter_name = 'level_range'
    
    def lookups(self, request, model_admin):
        return (
            ('1-5', 'Level 1-5'),
            ('6-10', 'Level 6-10'),
            ('11-15', 'Level 11-15'),
            ('16+', 'Level 16+'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == '1-5':
            return queryset.filter(current_level__gte=1, current_level__lte=5)
        if self.value() == '6-10':
            return queryset.filter(current_level__gte=6, current_level__lte=10)
        if self.value() == '11-15':
            return queryset.filter(current_level__gte=11, current_level__lte=15)
        if self.value() == '16+':
            return queryset.filter(current_level__gte=16)


@admin.register(ExpLog)
class ExpLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'exp_earned', 'description_preview', 'created_at')
    list_filter = (ExpEarnedFilter, 'activity_type', 'created_at')
    search_fields = ('user__username', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    # Bulk actions
    actions = ['export_selected_to_csv']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Activity Details', {
            'fields': ('activity_type', 'exp_earned', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def description_preview(self, obj):
        """Preview description (truncated)"""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_preview.short_description = 'Description'
    
    def export_selected_to_csv(self, request, queryset):
        """Bulk action to export selected EXP logs to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="exp_logs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Activity Type', 'EXP Earned', 'Description', 'Created At'])
        
        for log in queryset:
            writer.writerow([
                log.user.username,
                log.get_activity_type_display(),
                log.exp_earned,
                log.description,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_selected_to_csv.short_description = 'Export selected EXP logs to CSV'


@admin.register(Dungeon)
class DungeonAdmin(admin.ModelAdmin):
    list_display = ('name', 'scheduled_date', 'status', 'exp_reward', 'created_at')
    list_filter = ('status', 'scheduled_date')
    search_fields = ('name', 'description')
    date_hierarchy = 'scheduled_date'
    ordering = ('-scheduled_date',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Schedule', {
            'fields': ('scheduled_date', 'status')
        }),
        ('Rewards', {
            'fields': ('exp_reward',)
        }),
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'dungeon', 'attended', 'participation_exp', 'created_at')
    list_filter = ('attended', 'dungeon', 'created_at')
    search_fields = ('user__username', 'dungeon__name')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Information', {
            'fields': ('user', 'dungeon')
        }),
        ('Attendance', {
            'fields': ('attended', 'participation_exp')
        }),
    )


@admin.register(Sidequest)
class SidequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'due_date', 'status', 'exp_reward', 'late_exp_reward', 'created_at')
    list_filter = ('status', 'due_date')
    search_fields = ('title', 'description')
    date_hierarchy = 'due_date'
    ordering = ('-due_date',)


@admin.register(SidequestSubmission)
class SidequestSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'sidequest', 'submitted_at', 'grade', 'exp_earned')
    list_filter = ('sidequest', 'submitted_at', 'grade')
    search_fields = ('user__username', 'sidequest__title')
    date_hierarchy = 'submitted_at'
    ordering = ('-submitted_at',)


@admin.register(Boss)
class BossAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'type', 'base_score', 'bonus_applied', 'final_score', 'battle_date')
    list_filter = ('type', 'battle_date')
    search_fields = ('user__username', 'name', 'description')
    date_hierarchy = 'battle_date'
    ordering = ('-battle_date',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('type', 'name', 'description')
        }),
        ('Battle Details', {
            'fields': ('user', 'battle_date', 'base_score')
        }),
        ('Calculated Scores', {
            'fields': ('bonus_applied', 'final_score'),
            'description': 'These fields are auto-calculated based on player level and base score.'
        }),
    )
    
    readonly_fields = ('bonus_applied', 'final_score')


@admin.register(Punishment)
class PunishmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'severity', 'exp_penalty', 'status_effect', 'resolved', 'created_at')
    list_filter = ('type', 'severity', 'resolved', 'created_at')
    search_fields = ('user__username', 'description')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    # Bulk actions
    actions = ['resolve_selected', 'export_selected_to_csv']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'type', 'severity', 'description')
        }),
        ('Punishment Details', {
            'fields': ('exp_penalty', 'status_effect', 'duration_days')
        }),
        ('Status', {
            'fields': ('resolved', 'resolved_at')
        }),
        ('Additional', {
            'fields': ('evidence', 'created_by')
        }),
    )
    
    readonly_fields = ('created_by', 'resolved_at')
    
    def resolve_selected(self, request, queryset):
        """Bulk action to resolve selected punishments"""
        from django.utils import timezone
        from core.models import StatusEffect
        
        count = 0
        for punishment in queryset.filter(resolved=False):
            punishment.resolved = True
            punishment.resolved_at = timezone.now()
            punishment.save()
            
            # Deactivate related status effects
            StatusEffect.objects.filter(
                user=punishment.user,
                is_active=True,
                description__startswith=f"Punishment effect: {punishment.description}"
            ).update(is_active=False)
            
            count += 1
        
        self.message_user(request, f'{count} punishment(s) resolved successfully.')
    resolve_selected.short_description = 'Resolve selected punishments'
    
    def export_selected_to_csv(self, request, queryset):
        """Bulk action to export selected punishments to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="punishments_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Type', 'Severity', 'EXP Penalty', 'Status Effect', 'Resolved', 'Created At'])
        
        for punishment in queryset:
            writer.writerow([
                punishment.user.username,
                punishment.get_type_display(),
                punishment.get_severity_display(),
                punishment.exp_penalty,
                punishment.get_status_effect_display() if punishment.status_effect else '-',
                'Yes' if punishment.resolved else 'No',
                punishment.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_selected_to_csv.short_description = 'Export selected punishments to CSV'


@admin.register(StatusEffect)
class StatusEffectAdmin(admin.ModelAdmin):
    list_display = ('user', 'effect_type', 'exp_multiplier', 'is_active', 'start_date', 'end_date')
    list_filter = ('effect_type', 'is_active', 'start_date')
    search_fields = ('user__username', 'description')
    date_hierarchy = 'start_date'
    ordering = ('-start_date',)
    
    # Bulk actions
    actions = ['deactivate_selected']
    
    def deactivate_selected(self, request, queryset):
        """Bulk action to deactivate selected status effects"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f'{count} status effect(s) deactivated successfully.')
    deactivate_selected.short_description = 'Deactivate selected status effects'


# Note: User model is registered in accounts/admin.py
# To add bulk actions to User admin, modify accounts/admin.py instead
