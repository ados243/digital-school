"""Signaux : creation / mise a jour automatique des bulletins eleves."""

import threading
from contextlib import contextmanager

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

_local = threading.local()


@contextmanager
def suspendre_actualisation_bulletins():
    """Desactive temporairement les signaux (saisie groupée de notes)."""
    previous = getattr(_local, "suspendu", False)
    _local.suspendu = True
    try:
        yield
    finally:
        _local.suspendu = previous


def _est_suspendu():
    return getattr(_local, "suspendu", False)


def _refresh_inscription(inscription_id):
    if not inscription_id or _est_suspendu():
        return
    from inscription.models import Inscription
    from pedagogie.bulletin import actualiser_bulletin

    try:
        ins = Inscription.objects.select_related(
            "eleve", "classe", "classe__section", "classe__section__cycle",
            "classe__ecole", "annee_s",
        ).get(pk=inscription_id)
    except Inscription.DoesNotExist:
        return
    actualiser_bulletin(ins)


def _refresh_classe(classe_id, annee_id):
    if not classe_id or not annee_id or _est_suspendu():
        return
    from inscription.models import Annee_Scolaire, Classe
    from pedagogie.bulletin import actualiser_bulletins_classe

    try:
        classe = Classe.objects.select_related("section", "section__cycle", "ecole").get(pk=classe_id)
        annee = Annee_Scolaire.objects.get(pk=annee_id)
    except (Classe.DoesNotExist, Annee_Scolaire.DoesNotExist):
        return
    actualiser_bulletins_classe(classe, annee)


@receiver(post_save, sender="inscription.Inscription")
def creer_bulletin_a_inscription(sender, instance, created, **kwargs):
    if _est_suspendu():
        return
    from pedagogie.bulletin import actualiser_bulletin, obtenir_ou_creer_bulletin

    if created:
        obtenir_ou_creer_bulletin(instance)
    actualiser_bulletin(instance)


@receiver(post_save, sender="pedagogie.NoteEleve")
@receiver(post_delete, sender="pedagogie.NoteEleve")
def actualiser_bulletin_apres_note(sender, instance, **kwargs):
    _refresh_inscription(getattr(instance, "inscription_id", None))


@receiver(post_save, sender="pedagogie.TravailCote")
@receiver(post_delete, sender="pedagogie.TravailCote")
def actualiser_bulletins_apres_travail(sender, instance, **kwargs):
    _refresh_classe(
        getattr(instance, "classe_id", None),
        getattr(instance, "annee_scolaire_id", None),
    )
