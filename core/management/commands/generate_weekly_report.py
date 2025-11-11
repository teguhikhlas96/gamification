"""
Management command untuk generate weekly engagement report
Jalankan via cron job setiap minggu
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from core.models import ExpLog, Dungeon, Attendance, Sidequest, SidequestSubmission, Punishment
import csv
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Generate weekly engagement report'

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
        
        # Date range (last 7 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        
        # Generate report data
        total_players = User.objects.filter(role='player').count()
        active_players = User.objects.filter(
            role='player',
            exp_logs__created_at__gte=start_date
        ).distinct().count()
        
        total_exp_earned = ExpLog.objects.filter(
            created_at__gte=start_date
        ).aggregate(Sum('exp_earned'))['exp_earned__sum'] or 0
        
        total_activities = ExpLog.objects.filter(
            created_at__gte=start_date
        ).count()
        
        dungeons_attended = Attendance.objects.filter(
            attended=True,
            created_at__gte=start_date
        ).count()
        
        sidequests_submitted = SidequestSubmission.objects.filter(
            submitted_at__gte=start_date
        ).count()
        
        punishments_issued = Punishment.objects.filter(
            created_at__gte=start_date
        ).count()
        
        # Top active players
        top_players = User.objects.filter(
            role='player',
            exp_logs__created_at__gte=start_date
        ).annotate(
            exp_earned=Sum('exp_logs__exp_earned', filter=Q(exp_logs__created_at__gte=start_date))
        ).order_by('-exp_earned')[:10]
        
        # Generate CSV report
        filename = os.path.join(output_dir, f'weekly_report_{end_date.strftime("%Y%m%d")}.csv')
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Weekly Engagement Report'])
            writer.writerow(['Generated:', end_date.strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow(['Period:', f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'])
            writer.writerow([])
            
            # Summary
            writer.writerow(['Summary'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Players', total_players])
            writer.writerow(['Active Players (Last 7 Days)', active_players])
            writer.writerow(['Total EXP Earned', total_exp_earned])
            writer.writerow(['Total Activities', total_activities])
            writer.writerow(['Dungeons Attended', dungeons_attended])
            writer.writerow(['Sidequests Submitted', sidequests_submitted])
            writer.writerow(['Punishments Issued', punishments_issued])
            writer.writerow([])
            
            # Top Players
            writer.writerow(['Top 10 Active Players'])
            writer.writerow(['Rank', 'Username', 'EXP Earned', 'Level', 'Honor Points'])
            for idx, player in enumerate(top_players, start=1):
                writer.writerow([
                    idx,
                    player.username,
                    player.exp_earned or 0,
                    player.current_level,
                    player.honor_points
                ])
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Weekly report generated successfully: {filename}'
            )
        )

