"""
Installe et vérifie le stockage des vidéos de cours.

Usage :
    python manage.py installer_stockage_video
    python manage.py installer_stockage_video --test-cloud
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Prépare le stockage des vidéos de cours '
        '(dossier local, dépendances, config cloud optionnelle).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-cloud',
            action='store_true',
            help='Teste la connexion au bucket S3/R2 si configuré.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Installation - stockage videos de cours'))
        self._check_dependencies()
        local_dir = self._ensure_local_dir()
        cloud = self._report_cloud_config()

        if options['test_cloud']:
            if not cloud:
                raise CommandError(
                    'Cloud non configuré. Renseignez AWS_STORAGE_BUCKET_NAME '
                    '(et clés + endpoint) dans .env puis relancez avec --test-cloud.'
                )
            self._test_cloud_connection()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Installation terminee.'))
        if cloud:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Mode : cloud (bucket "{settings.AWS_STORAGE_BUCKET_NAME}").'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Mode : local prive -> {local_dir}\n'
                    'Les videos sont lues via /mon-espace/videos-cours/ (connexion requise).\n'
                    'Pour Cloudflare R2, decommentez les variables AWS_* dans .env.'
                )
            )

    def _check_dependencies(self):
        manquantes = []
        try:
            import storages  # noqa: F401
        except ImportError:
            manquantes.append('django-storages')
        try:
            import boto3  # noqa: F401
        except ImportError:
            manquantes.append('boto3')

        if manquantes:
            raise CommandError(
                'Dépendances manquantes : '
                + ', '.join(manquantes)
                + '.\nInstallez avec : pip install -r requirements.txt'
            )
        self.stdout.write(self.style.SUCCESS('[OK] Dependances django-storages et boto3'))

    def _ensure_local_dir(self) -> Path:
        from pedagogie.storage import cours_video_local_root

        video_dir = cours_video_local_root()
        video_dir.mkdir(parents=True, exist_ok=True)
        keep = video_dir / '.gitkeep'
        if not keep.exists():
            keep.write_text('', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'[OK] Dossier local prive pret : {video_dir}'))
        return video_dir

    def _report_cloud_config(self) -> bool:
        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '') or ''
        key = getattr(settings, 'AWS_ACCESS_KEY_ID', '') or ''
        secret = getattr(settings, 'AWS_SECRET_ACCESS_KEY', '') or ''
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)

        if not bucket:
            self.stdout.write('- Cloud : non configure (stockage local)')
            return False

        manques = []
        if not key:
            manques.append('AWS_ACCESS_KEY_ID')
        if not secret:
            manques.append('AWS_SECRET_ACCESS_KEY')
        if manques:
            raise CommandError(
                f'Bucket defini ({bucket}) mais variables manquantes : '
                + ', '.join(manques)
            )

        self.stdout.write(self.style.SUCCESS(f'[OK] Cloud configure — bucket : {bucket}'))
        if endpoint:
            self.stdout.write(f'  endpoint : {endpoint}')
        else:
            self.stdout.write('  endpoint : AWS S3 par defaut')
        expire = getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 3600)
        self.stdout.write(f'  URL signee : {expire}s')
        max_mb = getattr(settings, 'COURS_VIDEO_MAX_MB', 70)
        self.stdout.write(f'  taille max video : {max_mb} Mo (par fichier)')
        return True

    def _test_cloud_connection(self):
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        kwargs = {
            'service_name': 's3',
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
            'region_name': getattr(settings, 'AWS_S3_REGION_NAME', 'auto') or 'auto',
        }
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
        if endpoint:
            kwargs['endpoint_url'] = endpoint

        client = boto3.client(**kwargs)
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        try:
            client.head_bucket(Bucket=bucket)
        except (BotoCoreError, ClientError) as exc:
            raise CommandError(f'Échec connexion bucket « {bucket} » : {exc}') from exc

        # Écriture / lecture / suppression d'un petit objet de test
        key = f"{getattr(settings, 'COURS_VIDEO_LOCATION', 'cours_videos')}/.ds-install-check"
        try:
            # Pas d'ACL explicite : Cloudflare R2 / certains S3-compatibles ne les supportent pas.
            client.put_object(Bucket=bucket, Key=key, Body=b'digital-school-ok')
            client.delete_object(Bucket=bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise CommandError(
                f'Bucket accessible en lecture mais écriture échouée : {exc}'
            ) from exc

        self.stdout.write(self.style.SUCCESS(f'[OK] Test cloud (lecture/ecriture sur "{bucket}")'))
