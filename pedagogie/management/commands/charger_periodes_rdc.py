"""Charge trimestres/semestres et périodes bulletin selon le calendrier MINEDU-NC.

L'année scolaire est nationale (partagée par toutes les écoles).
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from inscription.models import Annee_Scolaire, Cycle
from pedagogie.calendrier_rdc import (
    MODE_PAR_CYCLE,
    annees_civiles_depuis_libelle,
    dates_annee_nationale,
    ordinal_periode,
    ordinal_semestre,
    ordinal_trimestre,
    resolve_date,
)
from pedagogie.models import DivisionAnnee, PeriodeBulletin
from pedagogie.periodes_utils import synchroniser_encours


class Command(BaseCommand):
    help = (
        "Crée / met à jour l'année scolaire nationale et les "
        "trimestres/semestres/périodes du bulletin (calendrier MINEDU-NC)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--annee',
            type=str,
            default=None,
            help="Libellé année nationale à traiter (ex. 2025-2026). Défaut : toutes.",
        )
        parser.add_argument(
            '--annee-id',
            type=int,
            default=None,
            help="Limiter à une année scolaire (id).",
        )
        parser.add_argument(
            '--creer',
            type=str,
            default=None,
            metavar='YYYY-YYYY',
            help="Créer l'année nationale si absente (ex. 2025-2026) puis charger les périodes.",
        )
        parser.add_argument(
            '--encours',
            action='store_true',
            help="Marquer l'année créée / ciblée comme année en cours.",
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help="Recréer les divisions/périodes existantes pour les cycles cibles.",
        )
        parser.add_argument(
            '--align-dates',
            action='store_true',
            help="Aligner date_debut/date_fin de l'annee sur le calendrier national (1 sept. -> 2 juil.).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['creer']:
            self._creer_annee(options['creer'], encours=options['encours'])

        annees = Annee_Scolaire.objects.all()
        if options['annee_id']:
            annees = annees.filter(pk=options['annee_id'])
        if options['annee']:
            annees = annees.filter(anne_scolaire=options['annee'])
        if options['creer'] and not options['annee'] and not options['annee_id']:
            annees = Annee_Scolaire.objects.filter(anne_scolaire=options['creer'])

        if not annees.exists():
            self.stdout.write(
                self.style.ERROR(
                    'Aucune annee scolaire trouvee. '
                    'Exemple : python manage.py charger_periodes_rdc --creer 2025-2026 --encours --align-dates'
                )
            )
            return

        cycles = {c.cycle: c for c in Cycle.objects.all()}
        manquants = [code for code in MODE_PAR_CYCLE if code not in cycles]
        if manquants:
            self.stdout.write(
                self.style.ERROR(
                    f'Cycles manquants : {", ".join(manquants)}. '
                    'Executez d\'abord : python manage.py charger_sections_rdc'
                )
            )
            return

        total_div = total_per = 0
        jour = date.today()
        for annee in annees:
            y0, y1 = annees_civiles_depuis_libelle(
                annee.anne_scolaire, annee.date_debut, annee.date_fin
            )
            self.stdout.write(f'\nAnnee nationale {annee.anne_scolaire} [{y0}-{y1}]')

            if options['align_dates'] or options['creer']:
                debut, fin = dates_annee_nationale(y0, y1)
                fields = []
                if annee.date_debut != debut or annee.date_fin != fin:
                    annee.date_debut = debut
                    annee.date_fin = fin
                    fields.extend(['date_debut', 'date_fin'])
                if options['encours'] and not annee.est_encoure:
                    annee.est_encoure = True
                    fields.append('est_encoure')
                if fields:
                    annee.save(update_fields=fields)
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ~ Dates annee alignees : {debut} -> {fin}'
                            + (' (en cours)' if annee.est_encoure else '')
                        )
                    )
            elif options['encours'] and not annee.est_encoure:
                annee.est_encoure = True
                annee.save(update_fields=['est_encoure'])

            for cycle_code, (type_div, structure) in MODE_PAR_CYCLE.items():
                cycle = cycles[cycle_code]
                if options['replace']:
                    PeriodeBulletin.objects.filter(
                        annee_scolaire=annee, cycle=cycle
                    ).delete()
                    DivisionAnnee.objects.filter(
                        annee_scolaire=annee, cycle=cycle
                    ).delete()

                for num_div, debut_t, fin_t, periodes in structure:
                    d_debut = resolve_date(y0, y1, *debut_t)
                    d_fin = resolve_date(y0, y1, *fin_t)
                    libelle_div = (
                        ordinal_trimestre(num_div)
                        if type_div == 'TRIMESTRE'
                        else ordinal_semestre(num_div)
                    )
                    div_encours = d_debut <= jour <= d_fin
                    division, created = DivisionAnnee.objects.update_or_create(
                        annee_scolaire=annee,
                        cycle=cycle,
                        type_division=type_div,
                        numero=num_div,
                        defaults={
                            'libelle': libelle_div,
                            'date_debut': d_debut,
                            'date_fin': d_fin,
                            'est_encours': div_encours,
                        },
                    )
                    if created:
                        total_div += 1
                        self.stdout.write(
                            f'  + {cycle_code} / {libelle_div} '
                            f'({d_debut.isoformat()} - {d_fin.isoformat()})'
                        )
                    else:
                        self.stdout.write(
                            f'  ~ {cycle_code} / {libelle_div} '
                            f'({d_debut.isoformat()} - {d_fin.isoformat()})'
                        )

                    for num_p, debut_p, fin_p in periodes:
                        p_debut = resolve_date(y0, y1, *debut_p)
                        p_fin = resolve_date(y0, y1, *fin_p)
                        per_encours = p_debut <= jour <= p_fin
                        periode, p_created = PeriodeBulletin.objects.update_or_create(
                            annee_scolaire=annee,
                            cycle=cycle,
                            numero=num_p,
                            defaults={
                                'division': division,
                                'libelle': ordinal_periode(num_p),
                                'date_debut': p_debut,
                                'date_fin': p_fin,
                                'est_encours': per_encours,
                            },
                        )
                        if p_created:
                            total_per += 1
                            self.stdout.write(
                                f'      + {periode.libelle} '
                                f'({p_debut.isoformat()} - {p_fin.isoformat()})'
                            )
                        else:
                            self.stdout.write(
                                f'      ~ {periode.libelle} '
                                f'({p_debut.isoformat()} - {p_fin.isoformat()})'
                            )

            synchroniser_encours(aujourdhui=jour, annee=annee)

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Termine : {total_div} division(s) creee(s), '
                f'{total_per} periode(s) creee(s) '
                f'(mises a jour appliquees pour le reste).'
            )
        )
        self.stdout.write(
            'Source : calendrier MINEDU-NC - '
            'Maternelle/Primaire -> 3 trimestres (6 periodes) ; '
            'CTEB + humanites -> 2 semestres (4 periodes).'
        )

    def _creer_annee(self, libelle, encours=False):
        try:
            y0, y1 = annees_civiles_depuis_libelle(libelle)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        debut, fin = dates_annee_nationale(y0, y1)
        annee, created = Annee_Scolaire.objects.get_or_create(
            anne_scolaire=libelle,
            defaults={
                'date_debut': debut,
                'date_fin': fin,
                'est_encoure': encours,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Annee nationale creee : {libelle} ({debut} -> {fin})'
                )
            )
        else:
            self.stdout.write(f'Annee nationale deja presente : {libelle}')
            if encours and not annee.est_encoure:
                annee.est_encoure = True
                annee.save(update_fields=['est_encoure'])
