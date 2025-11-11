from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    """
    Custom User model dengan fields tambahan untuk gamification
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('player', 'Player'),
    ]
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='player'
    )
    current_exp = models.IntegerField(default=0)
    current_level = models.IntegerField(default=1)
    total_exp = models.IntegerField(default=0)
    honor_points = models.IntegerField(default=100)
    
    def __str__(self):
        return self.username
    
    def is_admin(self):
        """Check jika user adalah admin"""
        return self.role == 'admin' or self.is_staff or self.is_superuser
    
    def is_player(self):
        """Check jika user adalah player"""
        return self.role == 'player'
    
    def get_absolute_url(self):
        """Redirect berdasarkan role"""
        if self.is_admin():
            return reverse('admin_dashboard:dashboard')
        elif self.is_player():
            return reverse('player:dashboard')
        else:
            return reverse('accounts:login')
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
