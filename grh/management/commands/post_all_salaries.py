from django.core.management.base import BaseCommand
from grh.models import Paie
from finances.views import _hoada_auto_post_salary_to_entries
import logging

class Command(BaseCommand):
    help = 'Passe automatiquement toutes les fiches de paie avec statut PAYE en écriture comptable OHADA'

    def handle(self, *args, **options):
        # Récupérer tous les salaires avec le statut 'PAYE'
        paies = Paie.objects.filter(statut_paiement="PAYE")
        
        self.stdout.write(f"Trouvé {paies.count()} salaires avec statut PAYE.")
        
        succes = 0
        erreurs = 0

        for paie in paies:
            try:
                from finances.models import Ecriture
                
                try:
                    ecole = paie.personnel.ecole
                except AttributeError:
                    ecole = None
                
                if not ecole:
                    continue
                    
                # Vérifier si l'écriture existe déjà
                ref_str = getattr(paie, 'reference_paiement', None) or f"SAL-{paie.id}"
                libelle = f"Paiement Salaire {paie.mois}/{paie.annee} - {paie.personnel.nom} - Réf {ref_str}"
                
                if Ecriture.objects.filter(ecole=ecole, libelle=libelle).exists():
                    self.stdout.write(self.style.WARNING(f"Écriture pour le salaire {ref_str} existe déjà. Ignoré."))
                    continue

                # Appeler la fonction de comptabilisation
                _hoada_auto_post_salary_to_entries(paie)
                succes += 1
                self.stdout.write(self.style.SUCCESS(f"Écritures générées pour le salaire de {paie.personnel.prenom}."))
            except Exception as e:
                erreurs += 1
                self.stdout.write(self.style.ERROR(f"Erreur pour le salaire {paie.id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nOpération terminée. {succes} écritures générées, {erreurs} erreurs."))
