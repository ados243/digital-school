from django.db import migrations, models
import django.db.models.deletion


def creer_config_centrale(apps, schema_editor):
    ConfigWhatsApp = apps.get_model("finances", "ConfigWhatsApp")
    if ConfigWhatsApp.objects.filter(ecole__isnull=True).exists():
        return
    source = (
        ConfigWhatsApp.objects.filter(actif=True).order_by("pk").first()
        or ConfigWhatsApp.objects.order_by("pk").first()
    )
    if source:
        ConfigWhatsApp.objects.create(
            ecole=None,
            actif=source.actif,
            provider=source.provider,
            api_token=source.api_token,
            instance_id=source.instance_id,
            api_url=source.api_url,
            indicatif_pays=source.indicatif_pays or "243",
            template_meta=source.template_meta,
            template_langue=source.template_langue or "fr",
            template_variables=source.template_variables
            or "eleve,montant_affiche,numero_recu,frais,classe,date",
            message_modele=source.message_modele,
        )
    else:
        ConfigWhatsApp.objects.create(
            ecole=None,
            actif=False,
            provider="ULTRAMSG",
            indicatif_pays="243",
            template_langue="fr",
            template_variables="eleve,montant_affiche,numero_recu,frais,classe,date",
            message_modele=(
                "Bonjour {parent},\n\n"
                "Paiement reçu pour {eleve} ({classe}) à {ecole}.\n"
                "Reçu : {numero_recu}\n"
                "Frais : {frais}\n"
                "Montant : {montant} {devise}\n"
                "Mode : {mode}\n"
                "Date : {date}\n\n"
                "Merci."
            ),
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0011_seed_type_frais_minerval"),
        ("inscription", "0007_annee_scolaire_nationale"),
    ]

    operations = [
        migrations.AlterField(
            model_name="configwhatsapp",
            name="ecole",
            field=models.OneToOneField(
                blank=True,
                help_text="Laisser vide : configuration centrale partagée par toutes les écoles.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="config_whatsapp",
                to="inscription.ecole",
            ),
        ),
        migrations.AlterField(
            model_name="notificationwhatsapp",
            name="ecole",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notif_whatsapp",
                to="inscription.ecole",
            ),
        ),
        migrations.RunPython(creer_config_centrale, noop),
    ]
