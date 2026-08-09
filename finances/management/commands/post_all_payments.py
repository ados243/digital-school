from django.core.management.base import BaseCommand
from finances.models import Paiement
from finances.views import _hoada_auto_post_payment_to_entries
import logging

class Command(BaseCommand):
    help = 'Passe automatiquement tous les paiements VALIDÉS en écriture comptable OHADA s\'ils ne le sont pas déjà'

    def handle(self, *args, **options):
        # Récupérer tous les paiements avec le statut 'VALIDE'
        paiements = Paiement.objects.filter(statut="VALIDE")
        
        self.stdout.write(f"Trouvé {paiements.count()} paiements avec statut VALIDE.")
        
        succes = 0
        erreurs = 0

        for paiement in paiements:
            try:
                # _hoada_auto_post_payment_to_entries crée une PieceComptable 
                # et les écritures correspondantes. S'il l'a déjà fait (comment vérifier ?)
                # Actuellement la logique dans _hoada_auto_post_payment_to_entries crée une pièce
                # basée sur numero_recu. On peut vérifier si la pièce existe.
                # Lisons le code de _hoada_auto_post_payment_to_entries : elle crée une PieceComptable 
                # avec reference=paiement.numero_recu.
                from finances.models import PieceComptable
                try:
                    ecole = paiement.eleve.classe.ecole
                except AttributeError:
                    ecole = getattr(paiement.eleve, 'ecole', None)
                        
                piece_existe = PieceComptable.objects.filter(ecole=ecole, reference=paiement.numero_recu).exists()
                
                if piece_existe:
                    self.stdout.write(self.style.WARNING(f"Pièce comptable pour le reçu {paiement.numero_recu} existe déjà. Ignoré."))
                    continue

                # Appeler la fonction existante pour générer l'écriture
                _hoada_auto_post_payment_to_entries(paiement)
                succes += 1
                self.stdout.write(self.style.SUCCESS(f"Écritures générées pour le reçu {paiement.numero_recu}."))
            except Exception as e:
                erreurs += 1
                self.stdout.write(self.style.ERROR(f"Erreur pour le reçu {paiement.numero_recu}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nOpération terminée. {succes} écritures générées, {erreurs} erreurs."))
