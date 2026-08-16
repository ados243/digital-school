# Generated manually for residence move Eleve -> Tuteur

from django.db import migrations, models
import django.db.models.deletion


def copier_residence_vers_tuteur(apps, schema_editor):
    Eleve = apps.get_model("inscription", "Eleve")
    Tuteur = apps.get_model("inscription", "Tuteur")

    for tuteur in Tuteur.objects.all():
        eleve = (
            Eleve.objects.filter(titeur_id=tuteur.id)
            .exclude(quartier_id__isnull=True)
            .order_by("-id")
            .first()
        )
        if not eleve:
            continue
        updates = {}
        if not tuteur.quartier_id and eleve.quartier_id:
            updates["quartier_id"] = eleve.quartier_id
        if not (tuteur.adresse or "").strip() and (eleve.adresse or "").strip():
            updates["adresse"] = eleve.adresse
        if updates:
            Tuteur.objects.filter(pk=tuteur.pk).update(**updates)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inscription", "0008_alter_tuteur_telephone2"),
    ]

    operations = [
        migrations.AddField(
            model_name="tuteur",
            name="quartier",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="inscription.quartier",
                verbose_name="Quartier de résidence",
            ),
        ),
        migrations.AddField(
            model_name="tuteur",
            name="adresse",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                verbose_name="Adresse de résidence",
            ),
        ),
        migrations.AlterField(
            model_name="tuteur",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.RunPython(copier_residence_vers_tuteur, noop_reverse),
        migrations.RemoveField(
            model_name="eleve",
            name="adresse",
        ),
        migrations.RemoveField(
            model_name="eleve",
            name="quartier",
        ),
    ]
