from django.db import migrations, models


def recopier_classe_vers_m2m(apps, schema_editor):
    CoursEnLigne = apps.get_model("pedagogie", "CoursEnLigne")
    CoursEnDirect = apps.get_model("pedagogie", "CoursEnDirect")
    for Model in (CoursEnLigne, CoursEnDirect):
        for obj in Model.objects.exclude(classe_id=None).iterator():
            obj.classes.add(obj.classe_id)


class Migration(migrations.Migration):

    dependencies = [
        ("inscription", "0012_eleve_sexe_sans_defaut"),
        ("pedagogie", "0018_edt_et_mobile_money"),
    ]

    operations = [
        migrations.AddField(
            model_name="coursenligne",
            name="classes",
            field=models.ManyToManyField(
                blank=True,
                help_text="Classes où ce cours est dispensé.",
                related_name="cours_en_ligne_partages",
                to="inscription.classe",
                verbose_name="Classes",
            ),
        ),
        migrations.AddField(
            model_name="coursendirect",
            name="classes",
            field=models.ManyToManyField(
                blank=True,
                help_text="Classes qui rejoignent cette séance.",
                related_name="cours_en_direct_partages",
                to="inscription.classe",
                verbose_name="Classes",
            ),
        ),
        migrations.RunPython(recopier_classe_vers_m2m, migrations.RunPython.noop),
    ]
