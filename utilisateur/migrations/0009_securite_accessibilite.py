# Generated manually — journaux d'accès, appareils, verrouillage connexion

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscription', '0012_eleve_sexe_sans_defaut'),
        ('utilisateur', '0008_avatar_upload_to'),
    ]

    operations = [
        migrations.CreateModel(
            name='JournalAcces',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=40)),
                ('ressource', models.CharField(blank=True, max_length=80)),
                ('identifiant', models.CharField(blank=True, max_length=64)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=300)),
                ('extra', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ecole', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='journaux_acces', to='inscription.ecole')),
                ('utilisateur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='journaux_acces', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': "Journal d'accès",
                'verbose_name_plural': "Journaux d'accès",
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='AppareilConnu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('empreinte', models.CharField(max_length=64)),
                ('libelle', models.CharField(blank=True, max_length=200)),
                ('dernier_vu', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appareils', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Appareil connu',
                'verbose_name_plural': 'Appareils connus',
                'unique_together': {('utilisateur', 'empreinte')},
            },
        ),
        migrations.CreateModel(
            name='VerrouillageConnexion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cle', models.CharField(max_length=190, unique=True)),
                ('echecs', models.PositiveIntegerField(default=0)),
                ('verrouille_jusquau', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Verrouillage connexion',
                'verbose_name_plural': 'Verrouillages connexion',
            },
        ),
        migrations.AddIndex(
            model_name='journalacces',
            index=models.Index(fields=['utilisateur', 'created_at'], name='utilisateur_utilisa_idx'),
        ),
        migrations.AddIndex(
            model_name='journalacces',
            index=models.Index(fields=['action', 'created_at'], name='utilisateur_action_idx'),
        ),
    ]
