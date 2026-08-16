# Generated manually — matricule élève unique globalement

from django.db import migrations, models


def dedupe_eleve_matricules(apps, schema_editor):
    Eleve = apps.get_model("inscription", "Eleve")
    prefixe = "ELV-"
    seen = set()
    max_seq = 0
    for m in Eleve.objects.filter(matricule__startswith=prefixe).values_list(
        "matricule", flat=True
    ):
        try:
            max_seq = max(max_seq, int(m[len(prefixe) :]))
        except ValueError:
            pass

    for obj in Eleve.objects.all().order_by("id"):
        mat = (obj.matricule or "").strip()
        if mat and mat not in seen:
            seen.add(mat)
            continue
        max_seq += 1
        new_mat = f"{prefixe}{max_seq:06d}"
        while new_mat in seen:
            max_seq += 1
            new_mat = f"{prefixe}{max_seq:06d}"
        obj.matricule = new_mat
        obj.save(update_fields=["matricule"])
        seen.add(new_mat)


class Migration(migrations.Migration):

    dependencies = [
        ("inscription", "0010_alter_eleve_nationalite"),
    ]

    operations = [
        migrations.RunPython(dedupe_eleve_matricules, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="eleve",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="eleve",
            name="matricule",
            field=models.CharField(max_length=10, unique=True),
        ),
    ]
