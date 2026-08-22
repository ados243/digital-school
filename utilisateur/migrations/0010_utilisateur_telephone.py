from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("utilisateur", "0009_securite_accessibilite"),
    ]

    operations = [
        migrations.AddField(
            model_name="utilisateur",
            name="telephone",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Numéro pour la double authentification (ex. +243…).",
                max_length=20,
                verbose_name="WhatsApp",
            ),
        ),
    ]
