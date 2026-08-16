from django.db import migrations


def seed_minerval(apps, schema_editor):
    Ecole = apps.get_model("inscription", "Ecole")
    TypeFrais = apps.get_model("finances", "TypeFrais")
    for ecole in Ecole.objects.all():
        TypeFrais.objects.get_or_create(
            ecole=ecole,
            libelle="Minerval",
            defaults={"description": "Frais scolaire"},
        )


def unseed_minerval(apps, schema_editor):
    TypeFrais = apps.get_model("finances", "TypeFrais")
    TypeFrais.objects.filter(libelle="Minerval", description="Frais scolaire").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0010_whatsapp_meta_template_vars"),
        ("inscription", "0010_alter_eleve_nationalite"),
    ]

    operations = [
        migrations.RunPython(seed_minerval, unseed_minerval),
    ]
