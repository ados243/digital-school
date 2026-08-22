from django.db import migrations, models
import django.db.models.deletion
import pedagogie.storage
import pedagogie.validators


class Migration(migrations.Migration):

    dependencies = [
        ('grh', '0011_edt_et_mobile_money'),
        ('inscription', '0012_eleve_sexe_sans_defaut'),
        ('pedagogie', '0019_cours_multi_classes'),
    ]

    operations = [
        migrations.CreateModel(
            name='RessourcePartagee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('type_fichier', models.CharField(
                    choices=[
                        ('VIDEO', 'Vidéo'),
                        ('PDF', 'PDF'),
                        ('IMAGE', 'Image'),
                        ('DOCUMENT', 'Document'),
                        ('AUTRE', 'Autre fichier'),
                    ],
                    default='DOCUMENT',
                    max_length=20,
                )),
                ('fichier', models.FileField(
                    blank=True,
                    null=True,
                    upload_to=pedagogie.storage.upload_to_ressource,
                    validators=[pedagogie.validators.validate_ressource_fichier],
                    verbose_name='Fichier',
                )),
                ('video', models.FileField(
                    blank=True,
                    null=True,
                    storage=pedagogie.storage.get_cours_video_storage,
                    upload_to=pedagogie.storage.upload_to_ressource_video,
                    validators=[pedagogie.validators.validate_cours_video],
                    verbose_name='Vidéo',
                )),
                ('publie', models.BooleanField(
                    default=True,
                    help_text='Décochez pour garder un brouillon.',
                    verbose_name='Visible par les élèves',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('annee_scolaire', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ressources_partagees',
                    to='inscription.annee_scolaire',
                )),
                ('classes', models.ManyToManyField(
                    help_text='Classes qui peuvent consulter cette ressource.',
                    related_name='ressources_partagees',
                    to='inscription.classe',
                    verbose_name='Classes',
                )),
                ('ecole', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ressources_partagees',
                    to='inscription.ecole',
                )),
                ('enseignant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ressources_partagees',
                    to='grh.personnel',
                )),
                ('matiere', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ressources_partagees',
                    to='pedagogie.matiere',
                )),
            ],
            options={
                'verbose_name': 'Ressource partagée',
                'verbose_name_plural': 'Ressources partagées',
                'ordering': ['-created_at'],
            },
        ),
    ]
