from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Q
from .models import User


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


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin interface untuk custom User model dengan gamification features
    """
    list_display = ('username', 'email', 'role', 'current_level', 'current_exp', 'total_exp', 'honor_points', 'is_staff', 'is_active')
    list_filter = (LevelRangeFilter, 'role', 'is_staff', 'is_active', 'current_level')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    # Bulk actions
    actions = ['export_selected_to_csv', 'reset_honor_points']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Gamification Fields', {
            'fields': ('role', 'current_exp', 'current_level', 'total_exp', 'honor_points')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Gamification Fields', {
            'fields': ('role', 'current_exp', 'current_level', 'total_exp', 'honor_points')
        }),
    )
    
    def export_selected_to_csv(self, request, queryset):
        """Bulk action to export selected users to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Username', 'Email', 'Role', 'Level', 'Total EXP', 'Honor Points'])
        
        for user in queryset:
            writer.writerow([
                user.username,
                user.email or '',
                user.get_role_display(),
                user.current_level,
                user.total_exp,
                user.honor_points
            ])
        
        return response
    export_selected_to_csv.short_description = 'Export selected users to CSV'
    
    def reset_honor_points(self, request, queryset):
        """Bulk action to reset honor points to default (100)"""
        count = queryset.filter(role='player').update(honor_points=100)
        self.message_user(request, f'{count} player(s) honor points reset to 100.')
    reset_honor_points.short_description = 'Reset honor points to 100 (players only)'
