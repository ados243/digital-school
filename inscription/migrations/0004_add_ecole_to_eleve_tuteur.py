# Generated manually for multi-tenant ecole on Eleve and Tuteur

import django.db.models.deletion
from django.db import migrations, models


def populate_ecole_from_inscriptions(apps, schema_editor):
    Eleve = apps.get_model('inscription', 'Eleve')
    Tuteur = apps.get_model('inscription', 'Tuteur')
    Inscription = apps.get_model('inscription', 'Inscription')
    Classe = apps.get_model('inscription', 'Classe')

    for eleve in Eleve.objects.all().order_by('id'):
        ins = Inscription.objects.filter(eleve_id=eleve.pk).order_by('-id').first()
        if ins:
            classe = Classe.objects.filter(pk=ins.classe_id).first()
            if classe:
                eleve.ecole_id = classe.ecole_id
                eleve.save(update_fields=['ecole_id'])
                tuteur = Tuteur.objects.filter(pk=eleve.titeur_id).first()
                if tuteur:
                    tuteur.ecole_id = classe.ecole_id
                    tuteur.save(update_fields=['ecole_id'])

    _dedupe_matricules(Eleve)
    _dedupe_matricules(Tuteur)


def _dedupe_matricules(model):
    seen = set()
    for obj in model.objects.all().order_by('id'):
        key = (obj.ecole_id, obj.matricule)
        if key in seen:
            suffix = str(obj.pk)[-3:]
            base = obj.matricule[: max(1, 10 - len(suffix) - 1)]
            obj.matricule = f"{base}-{suffix}"[:10]
            obj.save(update_fields=['matricule'])
            key = (obj.ecole_id, obj.matricule)
        seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ('inscription', '0003_alter_classe_options_alter_classe_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='tuteur',
            name='ecole',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to='inscription.ecole',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eleve',
            name='ecole',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to='inscription.ecole',
            ),
            preserve_default=False,
        ),
        migrations.RunPython(populate_ecole_from_inscriptions, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='eleve',
            options={'verbose_name': 'Élève', 'verbose_name_plural': 'Élèves'},
        ),
        migrations.AlterModelOptions(
            name='tuteur',
            options={'verbose_name': 'Tuteur', 'verbose_name_plural': 'Tuteurs'},
        ),
        migrations.AlterUniqueTogether(
            name='eleve',
            unique_together={('ecole', 'matricule')},
        ),
        migrations.AlterUniqueTogether(
            name='tuteur',
            unique_together={('ecole', 'matricule')},
        ),
    ]
