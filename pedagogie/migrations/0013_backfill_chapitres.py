from django.db import migrations


def assigner_chapitres_defaut(apps, schema_editor):
    CoursEnLigne = apps.get_model('pedagogie', 'CoursEnLigne')
    ChapitreCours = apps.get_model('pedagogie', 'ChapitreCours')
    LeconEnLigne = apps.get_model('pedagogie', 'LeconEnLigne')

    for cours in CoursEnLigne.objects.all():
        orphans = LeconEnLigne.objects.filter(cours=cours, chapitre__isnull=True)
        if orphans.exists():
            chapitre, _ = ChapitreCours.objects.get_or_create(
                cours=cours,
                ordre=1,
                defaults={'titre': 'Chapitre 1', 'publie': True},
            )
            orphans.update(chapitre=chapitre)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pedagogie', '0012_chapitres_sous_chapitres'),
    ]

    operations = [
        migrations.RunPython(assigner_chapitres_defaut, noop),
    ]
