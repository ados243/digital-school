from django.db.models.signals import post_save
from django.dispatch import receiver

from inscription.models import Ecole

from .defaults import assurer_types_frais_systeme


@receiver(post_save, sender=Ecole)
def creer_types_frais_systeme(sender, instance, created, **kwargs):
    if created:
        assurer_types_frais_systeme(instance)
