from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grh', '0009_contrat_unique_personnel'),
    ]

    operations = [
        migrations.AddField(
            model_name='personnel',
            name='email',
            field=models.EmailField(
                blank=True,
                help_text='Utilisé pour vérifier la création de compte et l’authentification à deux facteurs.',
                max_length=254,
                null=True,
                verbose_name='E-mail',
            ),
        ),
    ]
