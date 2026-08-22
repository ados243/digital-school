from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0016_budget_rubriques"),
    ]

    operations = [
        migrations.AlterField(
            model_name="configwhatsapp",
            name="provider",
            field=models.CharField(
                choices=[
                    ("BIRD", "Bird (WhatsApp)"),
                    ("ULTRAMSG", "Ultramsg"),
                    ("META", "Meta Cloud API (WhatsApp Business)"),
                    ("LOG", "Mode test (journal uniquement)"),
                ],
                default="BIRD",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="configwhatsapp",
            name="template_meta",
            field=models.CharField(
                blank=True,
                help_text="Slug du template Bird (ex. bird_delivery_update) ou nom du modèle Meta",
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="configwhatsapp",
            name="template_langue",
            field=models.CharField(
                blank=True,
                default="en",
                help_text="Langue du template (Bird : souvent en ; Meta : fr, fr_FR…)",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="configwhatsapp",
            name="api_token",
            field=models.TextField(
                blank=True,
                help_text="Token Ultramsg / Access token Meta (inutile avec Bird : la clé est dans .env)",
            ),
        ),
        migrations.AlterField(
            model_name="configwhatsapp",
            name="instance_id",
            field=models.CharField(
                blank=True,
                help_text="Instance ID Ultramsg ou Phone Number ID Meta (inutile avec Bird)",
                max_length=80,
            ),
        ),
    ]
