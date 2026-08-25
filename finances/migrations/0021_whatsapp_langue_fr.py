from django.db import migrations


def forcer_langue_fr(apps, schema_editor):
    ConfigWhatsApp = apps.get_model("finances", "ConfigWhatsApp")
    ConfigWhatsApp.objects.exclude(template_langue__istartswith="fr").update(
        template_langue="fr"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0020_whatsapp_meta_templates"),
    ]

    operations = [
        migrations.RunPython(forcer_langue_fr, migrations.RunPython.noop),
    ]
