"""Charge les cycles et sections du système scolaire congolais (MEPST / MINEDU-NC).

Referentiels :
- Loi-cadre n° 14/004 du 11 fevrier 2014 de l'enseignement national
- Programmes educatifs MEPST / MINEDU-NC (CTEB, humanites generales,
  techniques et professionnelles)
- Structure de l'enseignement formel : maternelle, primaire, secondaire

Organisation retenue dans Digital School
----------------------------------------
Cycles :
  MATERNELLE  — 3 ans (cycle unique)
  PRIMAIRE    — 6 ans (education de base, 2 x 3 ans)
  SECONDAIRE  — CTEB / tronc commun (2 ans : 1ere-2eme)
  HUMANITE    — humanites generales, techniques et professionnelles (3-4 ans)

Sections (filieres / niveaux pedagogiques) :
  Maternelle, Primaire, CTEB,
  Scientifique, Litteraire, Pedagogique, Commerciale et Gestion, Sociale,
  Technique, Professionnelle
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from inscription.models import Cycle, Section


CYCLES_RDC = [
    'MATERNELLE',
    'PRIMAIRE',
    'SECONDAIRE',
    'HUMANITE',
]

# (libelle section unique, code cycle)
SECTIONS_RDC = [
    ('Maternelle', 'MATERNELLE'),
    ('Primaire', 'PRIMAIRE'),
    ('CTEB', 'SECONDAIRE'),
    ('Scientifique', 'HUMANITE'),
    ('Litteraire', 'HUMANITE'),
    ('Pedagogique', 'HUMANITE'),
    ('Commerciale et Gestion', 'HUMANITE'),
    ('Sociale', 'HUMANITE'),
    ('Technique', 'HUMANITE'),
    ('Professionnelle', 'HUMANITE'),
]

# Anciens libelles reconnus pour une section canonique
ALIAS_VERS_CANONIQUE = {
    'maternelle': 'Maternelle',
    'MATERNELLE': 'Maternelle',
    'PRIMAIRE': 'Primaire',
    'primaire': 'Primaire',
    'SECONDAIRE': 'CTEB',
    'Secondaire': 'CTEB',
    'Tronc commun': 'CTEB',
    'Education de base': 'CTEB',
    'Littéraire': 'Litteraire',
    'Pédagogique': 'Pedagogique',
}


def _alias_pour(libelle):
    return [libelle] + [a for a, n in ALIAS_VERS_CANONIQUE.items() if n == libelle]


class Command(BaseCommand):
    help = (
        "Cree les cycles et sections du systeme scolaire congolais "
        "(MEPST / MINEDU-NC) dans la base de donnees."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Afficher ce qui serait cree sans ecrire en base.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options['dry_run']
        if dry:
            self.stdout.write(self.style.WARNING('Mode dry-run — aucune ecriture.'))

        cycles_crees = cycles_existants = 0
        for code in CYCLES_RDC:
            exists = Cycle.objects.filter(cycle=code).exists()
            if exists:
                cycles_existants += 1
            elif dry:
                cycles_crees += 1
                self.stdout.write(f'  + Cycle {code}')
            else:
                Cycle.objects.create(cycle=code)
                cycles_crees += 1
                self.stdout.write(self.style.SUCCESS(f'  + Cycle {code}'))

        sections_creees = sections_maj = sections_existantes = 0
        for libelle, cycle_code in SECTIONS_RDC:
            cycle = Cycle.objects.filter(cycle=cycle_code).first()
            if not cycle and not dry:
                self.stdout.write(self.style.ERROR(f'  ! Cycle manquant : {cycle_code}'))
                continue

            existante = Section.objects.filter(section__in=_alias_pour(libelle)).first()
            if existante:
                besoins_maj = (
                    existante.section != libelle
                    or (cycle and existante.cycle_id != cycle.id)
                )
                if besoins_maj:
                    if dry:
                        sections_maj += 1
                        self.stdout.write(
                            f'  ~ Section "{existante.section}" -> "{libelle}" ({cycle_code})'
                        )
                    else:
                        existante.section = libelle
                        existante.cycle = cycle
                        existante.save(update_fields=['section', 'cycle'])
                        sections_maj += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ~ Section "{libelle}" alignee sur {cycle_code}'
                            )
                        )
                else:
                    sections_existantes += 1
                continue

            if dry:
                sections_creees += 1
                self.stdout.write(f'  + Section {libelle} ({cycle_code})')
            else:
                Section.objects.create(section=libelle, cycle=cycle)
                sections_creees += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  + Section {libelle} ({cycle_code})')
                )

        self.stdout.write('')
        self.stdout.write(
            f'Cycles : {cycles_crees} cree(s), {cycles_existants} deja present(s).'
        )
        self.stdout.write(
            f'Sections : {sections_creees} creee(s), {sections_maj} mise(s) a jour, '
            f'{sections_existantes} deja presente(s).'
        )
        if not dry:
            self.stdout.write(self.style.SUCCESS('Referentiel scolaire RDC charge.'))
