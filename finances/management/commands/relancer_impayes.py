"""Relances WhatsApp des frais scolaires impayés."""

from django.core.management.base import BaseCommand

from finances.models import ConfigWhatsApp
from finances.relances import lister_dettes, relancer_dettes
from inscription.models import Ecole


class Command(BaseCommand):
    help = "Envoie une relance WhatsApp aux tuteurs dont le minerval n'est pas soldé."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--ecole", type=int, default=0, help="ID école (0 = toutes)")

    def handle(self, *args, **options):
        ecoles = Ecole.objects.filter(activation=True)
        if options["ecole"]:
            ecoles = ecoles.filter(pk=options["ecole"])
        total = 0
        for ecole in ecoles:
            config = ConfigWhatsApp.charger_pour_ecole(ecole)
            if not config or not config.actif:
                continue
            lignes, annee = lister_dettes(ecole)
            if not annee:
                self.stderr.write("Aucune année scolaire en cours.")
                return
            if options["dry_run"]:
                for ligne in lignes:
                    if not ligne["peut_envoyer"]:
                        continue
                    self.stdout.write(
                        f"[dry-run] +{ligne['telephone']} {ligne['message'][:80]}"
                    )
                    total += 1
                continue
            stats = relancer_dettes(ecole, lignes=lignes)
            total += stats["envoyes"]
            for err in stats["erreurs"]:
                self.stderr.write(err)
        self.stdout.write(self.style.SUCCESS(f"{total} relance(s) traitée(s)."))
