"""
Management command untuk generate monthly performance analytics
Jalankan via cron job setiap bulan
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from core.models import ExpLog, Dungeon, Attendance, Sidequest, SidequestSubmission, Punishment, Boss
import csv
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Generate monthly performance analytics report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='reports',
            help='Directory to save the report (default: reports)'
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Date range (last 30 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Generate comprehensive analytics
        total_players = User.objects.filter(role='player').count()
        active_players = User.objects.filter(
            role='player',
            exp_logs__created_at__gte=start_date
        ).distinct().count()
        
        # EXP Statistics
        exp_stats = ExpLog.objects.filter(
            created_at__gte=start_date
        ).aggregate(
            total_exp=Sum('exp_earned'),
            avg_exp=Avg('exp_earned'),
            total_activities=Count('id')
        )
        
        # Activity Distribution
        activity_distribution = ExpLog.objects.filter(
            created_at__gte=start_date
        ).values('activity_type').annotate(
            count=Count('id'),
            total_exp=Sum('exp_earned')
        )
        
        # Level Distribution
        level_distribution = User.objects.filter(role='player').values('current_level').annotate(
            count=Count('id')
        ).order_by('current_level')
        
        # Engagement Metrics
        dungeons_created = Dungeon.objects.filter(created_at__gte=start_date).count()
        dungeons_attended = Attendance.objects.filter(
            attended=True,
            created_at__gte=start_date
        ).count()
        
        sidequests_created = Sidequest.objects.filter(created_at__gte=start_date).count()
        sidequests_submitted = SidequestSubmission.objects.filter(
            submitted_at__gte=start_date
        ).count()
        sidequests_graded = SidequestSubmission.objects.filter(
            grade__isnull=False,
            submitted_at__gte=start_date
        ).count()
        
        boss_battles = Boss.objects.filter(battle_date__gte=start_date.date()).count()
        
        # Punishment Statistics
        punishments_issued = Punishment.objects.filter(created_at__gte=start_date).count()
        punishments_resolved = Punishment.objects.filter(
            resolved=True,
            resolved_at__gte=start_date
        ).count()
        
        # Top Performers
        top_players = User.objects.filter(role='player').annotate(
            exp_earned=Sum('exp_logs__exp_earned', filter=Q(exp_logs__created_at__gte=start_date)),
            activity_count=Count('exp_logs', filter=Q(exp_logs__created_at__gte=start_date))
        ).order_by('-exp_earned')[:20]
        
        # Generate CSV report
        filename = os.path.join(output_dir, f'monthly_report_{end_date.strftime("%Y%m%d")}.csv')
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Monthly Performance Analytics Report'])
            writer.writerow(['Generated:', end_date.strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow(['Period:', f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'])
            writer.writerow([])
            
            # Summary
            writer.writerow(['Summary'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Players', total_players])
            writer.writerow(['Active Players (Last 30 Days)', active_players])
            writer.writerow(['Total EXP Earned', exp_stats['total_exp'] or 0])
            writer.writerow(['Average EXP per Activity', round(exp_stats['avg_exp'] or 0, 2)])
            writer.writerow(['Total Activities', exp_stats['total_activities'] or 0])
            writer.writerow([])
            
            # Engagement Metrics
            writer.writerow(['Engagement Metrics'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Dungeons Created', dungeons_created])
            writer.writerow(['Dungeons Attended', dungeons_attended])
            writer.writerow(['Sidequests Created', sidequests_created])
            writer.writerow(['Sidequests Submitted', sidequests_submitted])
            writer.writerow(['Sidequests Graded', sidequests_graded])
            writer.writerow(['Boss Battles', boss_battles])
            writer.writerow(['Punishments Issued', punishments_issued])
            writer.writerow(['Punishments Resolved', punishments_resolved])
            writer.writerow([])
            
            # Activity Distribution
            writer.writerow(['Activity Distribution'])
            writer.writerow(['Activity Type', 'Count', 'Total EXP'])
            for item in activity_distribution:
                writer.writerow([
                    item['activity_type'],
                    item['count'],
                    item['total_exp'] or 0
                ])
            writer.writerow([])
            
            # Level Distribution
            writer.writerow(['Level Distribution'])
            writer.writerow(['Level', 'Player Count'])
            for item in level_distribution:
                writer.writerow([item['current_level'], item['count']])
            writer.writerow([])
            
            # Top Performers
            writer.writerow(['Top 20 Performers (Last 30 Days)'])
            writer.writerow(['Rank', 'Username', 'EXP Earned', 'Activities', 'Level', 'Honor Points'])
            for idx, player in enumerate(top_players, start=1):
                writer.writerow([
                    idx,
                    player.username,
                    player.exp_earned or 0,
                    player.activity_count or 0,
                    player.current_level,
                    player.honor_points
                ])
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Monthly report generated successfully: {filename}'
            )
        )

