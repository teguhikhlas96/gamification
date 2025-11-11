from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from accounts.models import User
from core.services import check_level_up, apply_level_bonus


@receiver(pre_save, sender=User)
def set_initial_level(sender, instance, **kwargs):
    """
    Set level 1 untuk user baru
    """
    if instance.pk is None:  # User baru
        instance.current_level = 1


@receiver(post_save, sender=User)
def auto_level_up_on_exp_change(sender, instance, created, **kwargs):
    """
    Signal untuk auto level-up ketika user EXP berubah
    Hanya check level up jika total_exp berubah
    """
    if created:
        return
    
    # Skip jika ini dipanggil dari check_level_up (untuk menghindari infinite loop)
    # Kita akan check level up di add_exp function, bukan di signal
    # Signal ini hanya untuk backup check jika ada perubahan manual
    pass

