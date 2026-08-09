"""Charge les matières du programme national de l'éducation (RDC).

Référentiels :
- MINEDU-NC — programmes maternel, primaire, secondaire
- Programme national de l'enseignement primaire (domaines & branches)
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from grh.models import Personnel
from inscription.models import Classe, Ecole, Section
from pedagogie.models import Matiere


# (code, libellé, coefficient) — programme national RDC
PROGRAMME_PAR_CYCLE = {
    'MATERNELLE': [
        ('FRAN', 'Éveil langagier / Français', '2.00'),
        ('LANG', 'Langue nationale / congolaise', '2.00'),
        ('MATH', 'Éveil mathématique', '2.00'),
        ('SCIE', 'Éveil scientifique', '1.00'),
        ('SOCI', 'Éveil social et environnement', '1.00'),
        ('ARTS', 'Éducation artistique', '1.00'),
        ('EPS', 'Éducation physique et sportive', '1.00'),
        ('MANU', 'Activités manuelles', '1.00'),
        ('RELI', 'Éducation religieuse / morale', '1.00'),
    ],
    'PRIMAIRE': [
        # Domaine des langues
        ('LANG', 'Langue congolaise / nationale', '2.00'),
        ('FRAN', 'Français', '4.00'),
        # Domaine mathématiques, sciences et technologie
        ('MATH', 'Mathématiques', '4.00'),
        ('SCEV', "Sciences d'éveil", '2.00'),
        ('TECH', 'Technologie', '1.00'),
        # Domaine univers social et environnement
        ('ECM', 'Éducation civique et morale', '2.00'),
        ('ESE', "Éducation pour la santé et l'environnement", '1.00'),
        # Domaine des arts
        ('ARTS', 'Éducation artistique', '1.00'),
        # Domaine développement personnel
        ('EPS', 'Éducation physique et sports', '2.00'),
        ('ITM', 'Initiation au travail manuel', '1.00'),
        ('RELI', 'Religion', '1.00'),
    ],
    'SECONDAIRE': [
        # Tronc commun / humanités de base (1ère–2ème / éducation de base)
        ('FRAN', 'Français', '4.00'),
        ('MATH', 'Mathématiques', '4.00'),
        ('ANGL', 'Anglais', '2.00'),
        ('LANG', 'Langue nationale', '1.00'),
        ('PHYS', 'Physique', '2.00'),
        ('CHIM', 'Chimie', '2.00'),
        ('BIO', 'Biologie', '2.00'),
        ('HIST', 'Histoire', '2.00'),
        ('GEO', 'Géographie', '2.00'),
        ('ECM', 'Éducation civique et morale', '1.00'),
        ('EPS', 'Éducation physique et sportive', '1.00'),
        ('INFO', 'Informatique', '1.00'),
        ('ARTS', 'Éducation artistique', '1.00'),
        ('RELI', 'Religion', '1.00'),
    ],
    'HUMANITE': [
        # Filière générale — préparation EXETAT
        ('FRAN', 'Français', '4.00'),
        ('MATH', 'Mathématiques', '4.00'),
        ('ANGL', 'Anglais', '2.00'),
        ('PHYS', 'Physique', '3.00'),
        ('CHIM', 'Chimie', '3.00'),
        ('BIO', 'Biologie', '3.00'),
        ('HIST', 'Histoire', '2.00'),
        ('GEO', 'Géographie', '2.00'),
        ('PHIL', 'Philosophie', '2.00'),
        ('ECO', 'Économie', '2.00'),
        ('ECM', 'Éducation civique', '1.00'),
        ('EPS', 'Éducation physique et sportive', '1.00'),
        ('INFO', 'Informatique', '1.00'),
        ('RELI', 'Religion', '1.00'),
    ],
}


def _cycle_key(section):
    """Détermine le programme à appliquer selon le cycle / libellé de section."""
    cycle = (section.cycle.cycle or '').upper()
    if cycle in PROGRAMME_PAR_CYCLE:
        return cycle

    nom = (section.section or '').upper()
    if 'MATER' in nom:
        return 'MATERNELLE'
    if 'PRIM' in nom:
        return 'PRIMAIRE'
    if (
        'HUMAN' in nom
        or 'LITE' in nom
        or 'TECHNI' in nom
        or 'COMMER' in nom
        or 'SCIENT' in nom
        or 'PEDAGO' in nom
        or 'SOCIAL' in nom
        or 'PROFESS' in nom
    ):
        return 'HUMANITE'
    if (
        'SECOND' in nom
        or 'EDUCATION DE BASE' in nom
        or 'CTEB' in nom
        or 'TRONC' in nom
        or nom == 'EB'
    ):
        return 'SECONDAIRE'
    return None


class Command(BaseCommand):
    help = (
        "Crée les matières du programme national RDC pour les sections "
        "des classes existantes (par école)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--ecole-id',
            type=int,
            default=None,
            help="Limiter à une école (sinon toutes les écoles ayant des classes).",
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help="Remplacer les matières existantes de la section avant import.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        ecole_id = options.get('ecole_id')
        replace = options.get('replace')

        classes = Classe.objects.select_related('section', 'section__cycle', 'ecole')
        if ecole_id:
            classes = classes.filter(ecole_id=ecole_id)

        if not classes.exists():
            self.stdout.write(self.style.WARNING("Aucune classe trouvée."))
            return

        # Sections réellement utilisées par au moins une classe, groupées par école
        paires = (
            classes.values_list('ecole_id', 'section_id')
            .distinct()
            .order_by('ecole_id', 'section_id')
        )

        total_cree = 0
        total_maj = 0
        total_ignore = 0

        for ecole_pk, section_pk in paires:
            ecole = Ecole.objects.get(pk=ecole_pk)
            section = Section.objects.select_related('cycle').get(pk=section_pk)
            programme_key = _cycle_key(section)

            if not programme_key:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{ecole.ecole}] Section « {section.section} » : "
                        f"cycle non reconnu ({section.cycle.cycle}), ignorée."
                    )
                )
                continue

            # Primaire / maternelle : pas d'enseignant de référence (titulaire de classe).
            # Secondaire / humanités : rattacher un enseignant de référence.
            titulaire_defaut = programme_key in ('PRIMAIRE', 'MATERNELLE')
            enseignant = None
            if not titulaire_defaut:
                enseignant = (
                    Personnel.objects.filter(ecole=ecole, fonction='Enseignant').first()
                    or Personnel.objects.filter(ecole=ecole).first()
                )
                if not enseignant:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [{ecole.ecole}] Aucun personnel pour rattacher les matières. "
                            "Créez au moins un enseignant GRH."
                        )
                    )
                    continue

            branches = PROGRAMME_PAR_CYCLE[programme_key]
            if titulaire_defaut:
                enseignant_label = 'titulaire de classe (défaut)'
            else:
                enseignant_label = f"{enseignant.prenom} {enseignant.nom}"
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"[{ecole.ecole}] / {section.section} "
                    f"({programme_key}, {len(branches)} matieres) "
                    f"- enseignant : {enseignant_label}"
                )
            )

            if replace:
                deleted, _ = Matiere.objects.filter(ecole=ecole, section=section).delete()
                if deleted:
                    self.stdout.write(f"    {deleted} matière(s) existante(s) supprimée(s).")

            for code, libelle, coef in branches:
                defaults = {
                    'libelle': libelle,
                    'coefficient': Decimal(coef),
                    'enserignant': enseignant,
                }
                matiere, created = Matiere.objects.update_or_create(
                    ecole=ecole,
                    section=section,
                    code=code,
                    defaults=defaults,
                )
                if created:
                    total_cree += 1
                    action = 'cree'
                else:
                    total_maj += 1
                    action = 'mise a jour'
                self.stdout.write(f"    [{code}] {libelle} (coef. {coef}) - {action}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Termine : {total_cree} creee(s), {total_maj} mise(s) a jour, "
                f"{total_ignore} ignoree(s)."
            )
        )
