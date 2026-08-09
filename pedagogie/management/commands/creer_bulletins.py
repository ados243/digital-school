"""Cree et actualise les bulletins de tous les eleves inscrits."""

from django.core.management.base import BaseCommand

from inscription.models import Inscription
from pedagogie.bulletin import actualiser_bulletin, obtenir_ou_creer_bulletin


class Command(BaseCommand):
    help = "Cree un bulletin pour chaque inscription et recalcule les totaux / %."

    def add_arguments(self, parser):
        parser.add_argument('--ecole-id', type=int, default=None)
        parser.add_argument('--annee-id', type=int, default=None)

    def handle(self, *args, **options):
        qs = Inscription.objects.select_related(
            'eleve', 'classe', 'classe__section', 'classe__section__cycle',
            'classe__ecole', 'annee_s',
        )
        if options['ecole_id']:
            qs = qs.filter(classe__ecole_id=options['ecole_id'])
        if options['annee_id']:
            qs = qs.filter(annee_s_id=options['annee_id'])

        crees = maj = 0
        for ins in qs.iterator(chunk_size=50):
            existed = hasattr(ins, 'bulletin')
            try:
                existed = bool(ins.bulletin)
            except Exception:
                existed = False
            obtenir_ou_creer_bulletin(ins)
            actualiser_bulletin(ins)
            if existed:
                maj += 1
            else:
                crees += 1
            self.stdout.write(
                f"  {'~' if existed else '+'} {ins.eleve} ({ins.classe.classe})"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {crees} cree(s), {maj} actualise(s)."
        ))
