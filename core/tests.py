"""
Tests untuk core app
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from core.models import Level, ExpLog, Dungeon, Attendance, Sidequest, SidequestSubmission, Boss, Punishment, StatusEffect
from core.services import add_exp, check_level_up, calculate_final_score, PunishmentService, check_honor_privileges

User = get_user_model()


class LevelModelTest(TestCase):
    """Tests untuk Level model"""
    
    def setUp(self):
        self.level, _ = Level.objects.get_or_create(
            level=1,
            defaults={
                'exp_required': 0,
                'bonus_description': "Starting level"
            }
        )
    
    def test_level_str(self):
        self.assertEqual(str(self.level), "Level 1 (0 EXP)")
    
    def test_level_ordering(self):
        Level.objects.get_or_create(level=2, defaults={'exp_required': 100})
        Level.objects.get_or_create(level=3, defaults={'exp_required': 250})
        levels = list(Level.objects.all())
        self.assertEqual(levels[0].level, 1)
        self.assertEqual(levels[1].level, 2)
        self.assertEqual(levels[2].level, 3)


class ExpLogModelTest(TestCase):
    """Tests untuk ExpLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123',
            role='player'
        )
    
    def test_exp_log_creation(self):
        exp_log = ExpLog.objects.create(
            user=self.user,
            activity_type='quest',
            exp_earned=50,
            description='Test quest'
        )
        self.assertEqual(exp_log.user, self.user)
        self.assertEqual(exp_log.exp_earned, 50)
        self.assertEqual(exp_log.activity_type, 'quest')
    
    def test_exp_log_ordering(self):
        ExpLog.objects.create(user=self.user, activity_type='quest', exp_earned=50, description='First')
        ExpLog.objects.create(user=self.user, activity_type='quest', exp_earned=30, description='Second')
        logs = list(ExpLog.objects.filter(user=self.user))
        # Should be ordered by -created_at (newest first)
        self.assertEqual(logs[0].description, 'Second')
        self.assertEqual(logs[1].description, 'First')


class AddExpServiceTest(TestCase):
    """Tests untuk add_exp service function"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123',
            role='player'
        )
        # Create level data
        Level.objects.get_or_create(level=1, defaults={'exp_required': 0})
        Level.objects.get_or_create(level=2, defaults={'exp_required': 100})
    
    def test_add_exp_basic(self):
        result = add_exp(self.user, 50, 'quest', 'Test quest')
        self.assertTrue(result['success'])
        self.assertEqual(result['new_exp'], 50)
        self.assertEqual(result['actual_amount'], 50)
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_exp, 50)
        self.assertEqual(self.user.total_exp, 50)
    
    def test_add_exp_level_up(self):
        # Set user to 95 EXP (close to level 2)
        self.user.current_exp = 95
        self.user.total_exp = 95
        self.user.save()
        
        result = add_exp(self.user, 10, 'quest', 'Level up quest')
        self.assertTrue(result['level_up'])
        self.assertEqual(result['new_level'], 2)
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_level, 2)
    
    def test_add_exp_negative(self):
        self.user.current_exp = 100
        self.user.save()
        result = add_exp(self.user, -20, 'punishment', 'Test penalty')
        self.assertTrue(result['success'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_exp, 80)


class CheckLevelUpTest(TestCase):
    """Tests untuk check_level_up function"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123',
            role='player'
        )
        Level.objects.get_or_create(level=1, defaults={'exp_required': 0})
        Level.objects.get_or_create(level=2, defaults={'exp_required': 100})
        Level.objects.get_or_create(level=3, defaults={'exp_required': 250})
    
    def test_no_level_up(self):
        self.user.current_exp = 50
        self.user.save()
        result = check_level_up(self.user)
        self.assertFalse(result['level_up'])
    
    def test_level_up_single(self):
        self.user.current_exp = 100
        self.user.current_level = 1
        self.user.save()
        result = check_level_up(self.user)
        self.assertTrue(result['level_up'])
        self.assertEqual(result['new_level'], 2)
    
    def test_level_up_multiple(self):
        self.user.current_exp = 250
        self.user.current_level = 1
        self.user.save()
        result = check_level_up(self.user)
        self.assertTrue(result['level_up'])
        self.assertEqual(result['new_level'], 3)


class CalculateFinalScoreTest(TestCase):
    """Tests untuk calculate_final_score function"""
    
    def test_no_bonus_level_1_5(self):
        # Level 1-5: no bonus
        for level in range(1, 6):
            result = calculate_final_score(80, level)
            self.assertEqual(result['final_score'], 80)
            self.assertFalse(result['bonus_applied'])
    
    def test_bonus_level_6_10(self):
        # Level 6-10: +5 points
        for level in range(6, 11):
            result = calculate_final_score(80, level)
            self.assertEqual(result['final_score'], 85)
            self.assertTrue(result['bonus_applied'])
            self.assertEqual(result['bonus_points'], 5)
    
    def test_bonus_level_11_15(self):
        # Level 11-15: +10 points
        for level in range(11, 16):
            result = calculate_final_score(80, level)
            self.assertEqual(result['final_score'], 90)
            self.assertTrue(result['bonus_applied'])
            self.assertEqual(result['bonus_points'], 10)
    
    def test_max_score_cap(self):
        # Score should not exceed 100
        result = calculate_final_score(98, 11)
        self.assertEqual(result['final_score'], 100)


class PunishmentServiceTest(TestCase):
    """Tests untuk PunishmentService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123',
            role='player',
            honor_points=100
        )
        Level.objects.get_or_create(level=1, defaults={'exp_required': 0})
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role='admin'
        )
    
    def test_plagiarism_punishment_minor(self):
        initial_exp = self.user.current_exp = 200
        self.user.save()
        
        PunishmentService.apply_plagiarism_punishment(
            user=self.user,
            severity='minor',
            created_by=self.admin
        )
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_exp, initial_exp - 100)
        self.assertEqual(self.user.honor_points, 90)  # 100 - 10
    
    def test_plagiarism_punishment_major(self):
        initial_exp = self.user.current_exp = 200
        self.user.save()
        
        PunishmentService.apply_plagiarism_punishment(
            user=self.user,
            severity='major',
            created_by=self.admin
        )
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_exp, initial_exp - 300)
        # Check status effect created
        status_effects = StatusEffect.objects.filter(user=self.user, is_active=True)
        self.assertTrue(status_effects.exists())
    
    def test_cheating_punishment_mini_boss(self):
        initial_exp = self.user.current_exp = 200
        self.user.save()
        
        PunishmentService.apply_cheating_punishment(
            user=self.user,
            boss_type='mini_boss',
            created_by=self.admin
        )
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_exp, initial_exp - 200)
        self.assertEqual(self.user.honor_points, 80)  # 100 - 20


class CheckHonorPrivilegesTest(TestCase):
    """Tests untuk check_honor_privileges function"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123',
            role='player'
        )
    
    def test_exalted_tier(self):
        self.user.honor_points = 900
        self.user.save()
        privileges = check_honor_privileges(self.user)
        self.assertEqual(privileges['honor_tier'].lower(), 'exalted')
        self.assertGreater(privileges['exp_multiplier_bonus'], 1.0)
    
    def test_outcast_tier(self):
        self.user.honor_points = 10
        self.user.save()
        privileges = check_honor_privileges(self.user)
        self.assertEqual(privileges['honor_tier'].lower(), 'outcast')
        self.assertFalse(privileges['can_join_dungeon'])
        self.assertFalse(privileges['can_submit_sidequest'])
        self.assertFalse(privileges['can_participate_boss'])


class DungeonModelTest(TestCase):
    """Tests untuk Dungeon model"""
    
    def setUp(self):
        self.dungeon = Dungeon.objects.create(
            name='Test Dungeon',
            description='Test description',
            scheduled_date=timezone.now() + timedelta(days=1),
            status='planned',
            exp_reward=50
        )
    
    def test_dungeon_str(self):
        self.assertEqual(str(self.dungeon), "Test Dungeon - Planned")
    
    def test_get_attended_count(self):
        user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123',
            role='player'
        )
        Attendance.objects.create(
            user=user,
            dungeon=self.dungeon,
            attended=True
        )
        self.assertEqual(self.dungeon.get_attended_count(), 1)


class SidequestModelTest(TestCase):
    """Tests untuk Sidequest model"""
    
    def setUp(self):
        self.sidequest = Sidequest.objects.create(
            title='Test Sidequest',
            description='Test description',
            instructions='Test instructions',
            due_date=timezone.now() + timedelta(days=7),
            exp_reward=200,
            late_exp_reward=100,
            status='active'
        )
    
    def test_sidequest_str(self):
        self.assertEqual(str(self.sidequest), "Test Sidequest - Active")
    
    def test_is_overdue(self):
        self.sidequest.due_date = timezone.now() - timedelta(days=1)
        self.sidequest.save()
        self.assertTrue(self.sidequest.is_overdue())


class IntegrationTest(TestCase):
    """Integration tests untuk views"""
    
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role='admin'
        )
        self.player = User.objects.create_user(
            username='player',
            email='player@example.com',
            password='playerpass123',
            role='player'
        )
        Level.objects.get_or_create(level=1, defaults={'exp_required': 0})
        Level.objects.get_or_create(level=2, defaults={'exp_required': 100})
    
    def test_admin_dashboard_access(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)
    
    def test_player_dashboard_access(self):
        self.client.login(username='player', password='playerpass123')
        response = self.client.get('/player-dashboard/')
        self.assertEqual(response.status_code, 200)
    
    def test_create_dungeon(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post('/admin/dungeons/create/', {
            'name': 'New Dungeon',
            'description': 'Test',
            'scheduled_date': (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'status': 'planned',
            'exp_reward': 50
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Dungeon.objects.filter(name='New Dungeon').exists())
    
    def test_submit_sidequest(self):
        self.client.login(username='player', password='playerpass123')
        sidequest = Sidequest.objects.create(
            title='Test Quest',
            description='Test',
            instructions='Test',
            due_date=timezone.now() + timedelta(days=7),
            status='active'
        )
        # Note: File upload test would require a test file
        # This is a simplified test
        response = self.client.get(f'/sidequests/{sidequest.id}/submit/')
        self.assertEqual(response.status_code, 200)
