from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0019_frais_classe"),
    ]

    operations = [
        migrations.AddField(
            model_name="configwhatsapp",
            name="template_relance",
            field=models.CharField(
                blank=True,
                default="relance_minerval",
                help_text="Modèle Meta relance minerval (ex. relance_minerval)",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="configwhatsapp",
            name="template_annonce",
            field=models.CharField(
                blank=True,
                default="annonce_ecole",
                help_text="Modèle Meta communication école → parents (ex. annonce_ecole)",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="configwhatsapp",
            name="template_otp",
            field=models.CharField(
                blank=True,
                default="code_verification",
                help_text="Modèle Meta code OTP (ex. code_verification)",
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="configwhatsapp",
            name="template_langue",
            field=models.CharField(
                blank=True,
                default="fr",
                help_text="Langue des templates Meta (souvent fr) ou Bird (souvent en)",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="configwhatsapp",
            name="template_meta",
            field=models.CharField(
                blank=True,
                help_text="Modèle Meta reçu de paiement (ex. recu_paiement) ou slug Bird",
                max_length=100,
            ),
        ),
    ]
