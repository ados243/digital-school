from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0018_edt_et_mobile_money"),
    ]

    operations = [
        migrations.AlterField(
            model_name="frais_scolaire",
            name="section",
            field=models.ForeignKey(
                blank=True,
                help_text="Barème pour toute la section. Laisser vide si le frais vise des classes précises.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="inscription.section",
            ),
        ),
        migrations.CreateModel(
            name="FraisClasse",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "classe",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="affectations_frais",
                        to="inscription.classe",
                    ),
                ),
                (
                    "frais",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="affectations_classe",
                        to="finances.frais_scolaire",
                    ),
                ),
            ],
            options={
                "verbose_name": "Frais par classe",
                "verbose_name_plural": "Frais par classe",
            },
        ),
        migrations.AddConstraint(
            model_name="fraisclasse",
            constraint=models.UniqueConstraint(
                fields=("frais", "classe"),
                name="uniq_frais_classe",
            ),
        ),
        migrations.AddField(
            model_name="frais_scolaire",
            name="classes",
            field=models.ManyToManyField(
                blank=True,
                related_name="frais_scolaires",
                through="finances.FraisClasse",
                to="inscription.classe",
            ),
        ),
    ]
