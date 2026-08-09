from datetime import date

from django.db import migrations, models


def _sync_encours(apps, schema_editor):
    DivisionAnnee = apps.get_model('pedagogie', 'DivisionAnnee')
    PeriodeBulletin = apps.get_model('pedagogie', 'PeriodeBulletin')
    Annee = apps.get_model('inscription', 'Annee_Scolaire')
    jour = date.today()

    DivisionAnnee.objects.filter(date_fin__lt=jour).update(est_encours=False)
    PeriodeBulletin.objects.filter(date_fin__lt=jour).update(est_encours=False)

    annee = Annee.objects.filter(est_encoure=True).order_by('-id').first()
    if not annee:
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


class Migration(migrations.Migration):

    dependencies = [
        ('pedagogie', '0013_backfill_chapitres'),
        ('inscription', '0007_annee_scolaire_nationale'),
    ]

    operations = [
        migrations.AddField(
            model_name='divisionannee',
            name='est_encours',
            field=models.BooleanField(
                default=False,
                help_text='Trimestre ou semestre actuellement actif. Désactivé automatiquement après la date de fin.',
                verbose_name='En cours',
            ),
        ),
        migrations.AddField(
            model_name='periodebulletin',
            name='est_encours',
            field=models.BooleanField(
                default=False,
                help_text='Période bulletin actuellement active. Désactivée automatiquement après la date de fin.',
                verbose_name='En cours',
            ),
        ),
        migrations.RunPython(_sync_encours, migrations.RunPython.noop),
    ]
