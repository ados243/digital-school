# Un seul contrat de travail par membre du personnel (établissement)

from django.db import migrations, models


def dedupe_contrats(apps, schema_editor):
    """Conserve un contrat par personnel (ACTIF prioritaire, sinon le plus récent)."""
    Contrat = apps.get_model("grh", "Contrat")
    seen = set()
    # ACTIF d'abord, puis date_debut desc, puis id desc
    ordre = {"ACTIF": 0, "SUSPENDU": 1, "TERMINE": 2}
    contrats = list(Contrat.objects.all())
    contrats.sort(
        key=lambda c: (
            c.personnel_id,
            ordre.get(c.statut, 9),
            -(c.date_debut.toordinal() if c.date_debut else 0),
            -c.pk,
        )
    )
    a_supprimer = []
    for c in contrats:
        if c.personnel_id in seen:
            a_supprimer.append(c.pk)
        else:
            seen.add(c.personnel_id)
    if a_supprimer:
        Contrat.objects.filter(pk__in=a_supprimer).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("grh", "0008_personnel_matricule_unique_global"),
    ]

    operations = [
        migrations.RunPython(dedupe_contrats, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="contrat",
            constraint=models.UniqueConstraint(
                fields=("personnel",),
                name="uniq_contrat_par_personnel",
            ),
        ),
    ]
