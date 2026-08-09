# Année scolaire nationale (plus de FK ecole) — calendrier partagé MINEDU-NC.

from django.db import migrations, models


def _assurer_une_seule_annee_en_cours(apps, schema_editor):
    Annee = apps.get_model('inscription', 'Annee_Scolaire')
    courantes = list(Annee.objects.filter(est_encoure=True).order_by('-date_debut', '-id'))
    if len(courantes) <= 1:
        return
    for annee in courantes[1:]:
        annee.est_encoure = False
        annee.save(update_fields=['est_encoure'])


class Migration(migrations.Migration):

    dependencies = [
        ('inscription', '0006_classe_titulaire'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='annee_scolaire',
            name='ecole',
        ),
        migrations.AlterField(
            model_name='annee_scolaire',
            name='anne_scolaire',
            field=models.CharField(
                help_text='Libellé national, ex. 2025-2026',
                max_length=9,
                unique=True,
                verbose_name='Année scolaire',
            ),
        ),
        migrations.AlterField(
            model_name='annee_scolaire',
            name='date_debut',
            field=models.DateField(verbose_name='Date de début'),
        ),
        migrations.AlterField(
            model_name='annee_scolaire',
            name='date_fin',
            field=models.DateField(verbose_name='Date de fin'),
        ),
        migrations.AlterField(
            model_name='annee_scolaire',
            name='est_encoure',
            field=models.BooleanField(
                default=False,
                help_text='Une seule année nationale peut être marquée en cours.',
                verbose_name='Année en cours',
            ),
        ),
        migrations.AlterModelOptions(
            name='annee_scolaire',
            options={
                'ordering': ['-est_encoure', '-anne_scolaire'],
                'verbose_name': 'Année scolaire',
                'verbose_name_plural': 'Années scolaires',
            },
        ),
        migrations.RunPython(_assurer_une_seule_annee_en_cours, migrations.RunPython.noop),
    ]
