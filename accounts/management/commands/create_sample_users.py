from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Membuat sample users untuk testing'

    def handle(self, *args, **options):
        # Sample admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@classcraft.com',
                'role': 'admin',
                'current_level': 10,
                'current_exp': 5000,
                'total_exp': 50000,
                'honor_points': 1000,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Admin user created: {admin_user.username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user already exists: {admin_user.username}'))

        # Sample player users
        sample_players = [
            {
                'username': 'player1',
                'email': 'player1@classcraft.com',
                'role': 'player',
                'current_level': 5,
                'current_exp': 2500,
                'total_exp': 15000,
                'honor_points': 500,
            },
            {
                'username': 'player2',
                'email': 'player2@classcraft.com',
                'role': 'player',
                'current_level': 3,
                'current_exp': 1200,
                'total_exp': 5000,
                'honor_points': 300,
            },
            {
                'username': 'player3',
                'email': 'player3@classcraft.com',
                'role': 'player',
                'current_level': 1,
                'current_exp': 100,
                'total_exp': 100,
                'honor_points': 100,
            },
        ]

        for player_data in sample_players:
            player, created = User.objects.get_or_create(
                username=player_data['username'],
                defaults=player_data
            )
            if created:
                player.set_password('player123')
                player.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Player created: {player.username} (Level {player.current_level})'))
            else:
                self.stdout.write(self.style.WARNING(f'Player already exists: {player.username}'))

        self.stdout.write(self.style.SUCCESS('\n✓ Sample users creation completed!'))
        self.stdout.write(self.style.SUCCESS('\nLogin credentials:'))
        self.stdout.write(self.style.SUCCESS('Admin: admin / admin123'))
        self.stdout.write(self.style.SUCCESS('Players: player1, player2, player3 / player123'))

