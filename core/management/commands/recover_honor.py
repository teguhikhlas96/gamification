"""
Management command untuk recover honor points secara gradual untuk semua players
Jalankan command ini secara berkala (misalnya via cron job) untuk gradual recovery
"""

from django.core.management.base import BaseCommand
from accounts.models import User
from core.services import PunishmentService


class Command(BaseCommand):
    help = 'Recover honor points untuk semua players secara gradual'

    def add_arguments(self, parser):
        parser.add_argument(
            '--amount',
            type=int,
            default=1,
            help='Jumlah honor points yang di-recover per user (default: 1)'
        )
        parser.add_argument(
            '--max-honor',
            type=int,
            default=1000,
            help='Maximum honor points (default: 1000)'
        )

    def handle(self, *args, **options):
        amount = options['amount']
        max_honor = options['max_honor']
        
        players = User.objects.filter(role='player')
        recovered_count = 0
        total_recovered = 0
        
        self.stdout.write(f'Memulai honor recovery untuk {players.count()} players...')
        
        for player in players:
            # Skip jika sudah mencapai max honor
            if player.honor_points >= max_honor:
                continue
            
            old_honor = player.honor_points
            if PunishmentService.recover_honor_points(player, amount):
                recovered_count += 1
                total_recovered += (player.honor_points - old_honor)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{player.username}: {old_honor} → {player.honor_points} (+{player.honor_points - old_honor})'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nHonor recovery selesai! {recovered_count} players recovered, total: +{total_recovered} honor points'
            )
        )

