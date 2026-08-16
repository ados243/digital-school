# Generated manually — matricule personnel (professeur) unique globalement

from django.db import migrations, models


def dedupe_personnel_matricules(apps, schema_editor):
    Personnel = apps.get_model("grh", "Personnel")
    prefixe = "PER-"
    seen = set()
    max_seq = 0
    for m in Personnel.objects.filter(matricule__startswith=prefixe).values_list(
        "matricule", flat=True
    ):
        try:
            max_seq = max(max_seq, int(m[len(prefixe) :]))
        except ValueError:
            pass

    for obj in Personnel.objects.all().order_by("id"):
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
        ("grh", "0007_personnel_fonction_promoteur"),
    ]

    operations = [
        migrations.RunPython(dedupe_personnel_matricules, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="personnel",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="personnel",
            name="matricule",
            field=models.CharField(max_length=10, unique=True),
        ),
    ]
