"""Synchronisation du statut « en cours » des trimestres / semestres / périodes."""

from datetime import date

from inscription.models import Annee_Scolaire

from .models import DivisionAnnee, PeriodeBulletin


def desactiver_periodes_expirees(aujourdhui=None):
    """Passe automatiquement ``est_encours=False`` si la date de fin est dépassée."""
    jour = aujourdhui or date.today()
    n_div = DivisionAnnee.objects.filter(est_encours=True, date_fin__lt=jour).update(
        est_encours=False
    )
    n_per = PeriodeBulletin.objects.filter(est_encours=True, date_fin__lt=jour).update(
        est_encours=False
    )
    return n_div, n_per


def synchroniser_encours(aujourdhui=None, annee=None):
    """Désactive les expirés, puis active la division/période couvrant la date du jour.

    Une seule division et une seule période « en cours » par cycle et année.
    """
    jour = aujourdhui or date.today()
    desactiver_periodes_expirees(jour)

    if annee is None:
        annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    if annee is None:
        return

    cycle_ids = (
        DivisionAnnee.objects.filter(annee_scolaire=annee)
        .values_list('cycle_id', flat=True)
        .distinct()
    )
    for cycle_id in cycle_ids:
        DivisionAnnee.objects.filter(
            annee_scolaire=annee, cycle_id=cycle_id
        ).update(est_encours=False)
        DivisionAnnee.objects.filter(
            annee_scolaire=annee,
            cycle_id=cycle_id,
            date_debut__lte=jour,
            date_fin__gte=jour,
        ).update(est_encours=True)

        PeriodeBulletin.objects.filter(
            annee_scolaire=annee, cycle_id=cycle_id
        ).update(est_encours=False)
        PeriodeBulletin.objects.filter(
            annee_scolaire=annee,
            cycle_id=cycle_id,
            date_debut__lte=jour,
            date_fin__gte=jour,
        ).update(est_encours=True)


def marquer_division_encours(division):
    """Active une division ; désactive les autres du même cycle/année. Refuse si expirée."""
    jour = date.today()
    if division.date_fin < jour:
        division.est_encours = False
        division.save(update_fields=['est_encours'])
        return False
    DivisionAnnee.objects.filter(
        annee_scolaire=division.annee_scolaire,
        cycle=division.cycle,
    ).exclude(pk=division.pk).update(est_encours=False)
    division.est_encours = True
    division.save(update_fields=['est_encours'])
    return True


def marquer_periode_encours(periode):
    """Active une période ; désactive les autres du même cycle/année. Refuse si expirée."""
    jour = date.today()
    if periode.date_fin < jour:
        periode.est_encours = False
        periode.save(update_fields=['est_encours'])
        return False
    PeriodeBulletin.objects.filter(
        annee_scolaire=periode.annee_scolaire,
        cycle=periode.cycle,
    ).exclude(pk=periode.pk).update(est_encours=False)
    periode.est_encours = True
    periode.save(update_fields=['est_encours'])
    return True


def resume_encours(annee=None, aujourdhui=None):
    """Liste compacte des divisions/périodes en cours (après sync des expirés)."""
    jour = aujourdhui or date.today()
    desactiver_periodes_expirees(jour)
    if annee is None:
        annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    if annee is None:
        return {'annee': None, 'lignes': []}

    lignes = []
    divisions = (
        DivisionAnnee.objects.filter(annee_scolaire=annee, est_encours=True)
        .select_related('cycle')
        .order_by('cycle__cycle', 'numero')
    )
    periodes = {
        (p.cycle_id): p
        for p in (
            PeriodeBulletin.objects.filter(annee_scolaire=annee, est_encours=True)
            .select_related('cycle', 'division')
            .order_by('cycle__cycle', 'numero')
        )
    }
    for div in divisions:
        lignes.append({
            'cycle': div.cycle,
            'division': div,
            'periode': periodes.get(div.cycle_id),
        })
    # Cycles avec seulement une période en cours (sans division)
    for cycle_id, periode in periodes.items():
        if not any(l['cycle'].id == cycle_id for l in lignes):
            lignes.append({
                'cycle': periode.cycle,
                'division': periode.division,
                'periode': periode,
            })
    return {'annee': annee, 'lignes': lignes, 'aujourdhui': jour}
