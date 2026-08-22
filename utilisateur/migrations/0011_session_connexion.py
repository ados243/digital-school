from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("utilisateur", "0010_utilisateur_telephone"),
    ]

    operations = [
        migrations.CreateModel(
            name="SessionConnexion",
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
                ("cle_session", models.CharField(db_index=True, max_length=40)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=300)),
                (
                    "mfa",
                    models.BooleanField(
                        default=False, verbose_name="Double authentification"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("revoquee", models.BooleanField(default=False)),
                (
                    "utilisateur",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions_connexion",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Session de connexion",
                "verbose_name_plural": "Sessions de connexion",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="sessionconnexion",
            index=models.Index(
                fields=["utilisateur", "ended_at"],
                name="utilisateur_utilisa_ended_idx",
            ),
        ),
    ]
