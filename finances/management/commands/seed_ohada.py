from django.core.management.base import BaseCommand
from finances.models import CompteComptable, JournalComptable
from inscription.models import Ecole

class Command(BaseCommand):
    help = 'Peuple la base de données avec un plan comptable SYSCOHADA de base pour une école'

    def handle(self, *args, **options):
        # Récupérer la première école (ou None si aucune)
        ecole = Ecole.objects.first()

        if not ecole:
            self.stdout.write(self.style.WARNING("Aucune école n'existe dans la base. Les comptes seront globaux (ecole=None)."))

        # Plan comptable OHADA simplifié (orienté école)
        comptes = [
            # CLASSE 1 : RESSOURCES DURABLES
            ("100000", "Capital social"),
            ("110000", "Réserves"),
            ("130000", "Résultat net de l'exercice"),
            
            # CLASSE 2 : ACTIFS IMMOBILISÉS
            ("210000", "Immobilisations incorporelles"),
            ("230000", "Bâtiments et installations"),
            ("240000", "Matériel, mobilier et actifs biologiques"),
            ("244000", "Matériel de bureau et informatique"),
            
            # CLASSE 3 : STOCKS
            ("310000", "Marchandises / Fournitures scolaires"),
            
            # CLASSE 4 : TIERS
            ("401000", "Fournisseurs d'exploitation"),
            ("411000", "Clients / Élèves (Créances de scolarité)"),
            ("411100", "Élèves - Frais obligatoires"),
            ("422000", "Personnel - Rémunérations dues"),
            ("430000", "État et collectivités publiques"),
            ("440000", "Associés et Administrateurs"),
            
            # CLASSE 5 : TRÉSORERIE
            ("521000", "Banques locales"),
            ("565000", "Dépôts de monnaie électronique (Mobile Money)"),
            ("571000", "Caisse principale"),
            
            # CLASSE 6 : CHARGES
            ("600000", "Achats de fournitures"),
            ("620000", "Services extérieurs (loyers, entretien)"),
            ("630000", "Frais de transport"),
            ("640000", "Services bancaires"),
            ("660000", "Charges de personnel (Salaires)"),
            
            # CLASSE 7 : PRODUITS
            ("706000", "Services vendus / Frais de scolarité"),
            ("706100", "Frais d'inscription"),
            ("706200", "Minerval / Frais mensuels"),
            ("770000", "Revenus financiers"),
        ]

        journaux = [
            ("ACHAT", "Journal des Achats"),
            ("VENTE", "Journal des Ventes / Frais scolaires"),
            ("CAISSE", "Journal de Caisse"),
            ("BANQUE", "Journal de Banque"),
            ("MMONEY", "Journal Mobile Money"),
            ("OD", "Opérations Diverses"),
        ]

        # Insertion des comptes
        comptes_crees = 0
        for numero, libelle in comptes:
            _, created = CompteComptable.objects.get_or_create(
                ecole=ecole,
                numero=numero,
                defaults={"libelle": libelle}
            )
            if created:
                comptes_crees += 1

        # Insertion des journaux
        journaux_crees = 0
        for code, libelle in journaux:
            _, created = JournalComptable.objects.get_or_create(
                ecole=ecole,
                code=code,
                defaults={"libelle": libelle}
            )
            if created:
                journaux_crees += 1

        self.stdout.write(self.style.SUCCESS(f'Succès ! {comptes_crees} comptes créés et {journaux_crees} journaux créés.'))
