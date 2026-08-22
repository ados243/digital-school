from django.db import models
from inscription.models import Ecole,Quartier
from utilisateur.models import Utilisateur
# Create your models here.
class Personnel(models.Model):
    Sexe_choices = [
        ('Masculin', 'M'),
        ('Feminin', 'F'),
    ]
    FONCTION_CHOICES = [
        ('Directeur', 'Directeur'),
        ('Directeur des études', 'Directeur des études'),
        ('Préfet', 'Préfet'),
        ('Promoteur', 'Promoteur'),
        ('Enseignant', 'Enseignant'),
        ('Trésorier', 'Trésorier'),
        ('Caissier', 'Caissier'),
        ('Comptable', 'Comptable'),
        ('Secrétaire', 'Secrétaire'),
        ('Surveillant', 'Surveillant'),
        ('Autre', 'Autre'),
    ]
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE)
    # Compte de connexion rattaché a posteriori (auto-inscription "corps professoral").
    utilisateur = models.OneToOneField(
        Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name='personnel'
    )
    nom = models.CharField(max_length=250)
    Post_nom = models.CharField(max_length=250)
    prenom = models.CharField(max_length=250)
    sexe = models.CharField(max_length=20, choices=Sexe_choices, default='Masculin')
    date_de_naissance = models.DateField()
    nationalite = models.CharField(max_length=50)
    quartier = models.ForeignKey(Quartier, on_delete=models.DO_NOTHING)
    adresse = models.CharField(max_length=200)
    photo = models.ImageField(null=True, blank=True)
    matricule = models.CharField(max_length=10, unique=True)
    telephone = models.CharField(max_length=13)
    email = models.EmailField(
        null=True,
        blank=True,
        verbose_name='E-mail',
        help_text='Utilisé pour vérifier la création de compte et l’authentification à deux facteurs.',
    )
    fonction = models.CharField(max_length=30, choices=FONCTION_CHOICES, default='Enseignant')

    class Meta:
        verbose_name = "Personnel"
        verbose_name_plural = "Personnel"

    def generer_matricule(self):
        """Matricule séquentiel du type PER-000001, unique dans toute l'application."""
        prefixe = "PER-"
        dernier = (
            Personnel.objects.filter(matricule__startswith=prefixe)
            .order_by("matricule")
            .last()
        )
        sequence = 0
        if dernier:
            try:
                sequence = int(dernier.matricule[len(prefixe):])
            except ValueError:
                sequence = Personnel.objects.count()
        return f"{prefixe}{sequence + 1:06d}"

    def save(self, *args, **kwargs):
        if not self.matricule and self.ecole_id:
            self.matricule = self.generer_matricule()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

class Contrat(models.Model):
    TYPE_CONTRAT_CHOICES = [
        ('CDI', 'CDI (Durée Indéterminée)'),
        ('CDD', 'CDD (Durée Déterminée)'),
        ('PRESTATAIRE', 'Prestataire externe'),
        ('STAGE', 'Stagiaire'),
    ]
    STATUT_CHOICES = [
        ('ACTIF', 'Actif'),
        ('SUSPENDU', 'Suspendu'),
        ('TERMINE', 'Terminé'),
    ]
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='contrats')
    type_contrat = models.CharField(max_length=20, choices=TYPE_CONTRAT_CHOICES, default='CDI')
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    salaire_base = models.DecimalField(max_digits=12, decimal_places=2)
    devise = models.ForeignKey('finances.Devise', on_delete=models.PROTECT)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='ACTIF')

    class Meta:
        verbose_name = "Contrat"
        verbose_name_plural = "Contrats"
        constraints = [
            models.UniqueConstraint(
                fields=["personnel"],
                name="uniq_contrat_par_personnel",
            )
        ]

    def __str__(self):
        return f"Contrat {self.type_contrat} - {self.personnel.nom}"

class Conge(models.Model):
    TYPE_CONGE_CHOICES = [
        ('ANNUEL', 'Congé Annuel'),
        ('MALADIE', 'Congé Maladie'),
        ('MATERNITE', 'Congé Maternité'),
        ('SANS_SOLDE', 'Congé Sans Solde'),
        ('AUTRE', 'Autre'),
    ]
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En Attente'),
        ('APPROUVE', 'Approuvé'),
        ('REJETE', 'Rejeté'),
    ]
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='conges')
    type_conge = models.CharField(max_length=30, choices=TYPE_CONGE_CHOICES, default='ANNUEL')
    date_debut = models.DateField()
    date_fin = models.DateField()
    motif = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')

    def __str__(self):
        return f"Congé {self.type_conge} - {self.personnel.nom}"

class Presence(models.Model):
    STATUT_CHOICES = [
        ('PRESENT', 'Présent'),
        ('ABSENT', 'Absent'),
        ('RETARD', 'Retard'),
        ('CONGE', 'En congé'),
    ]
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='presences')
    date = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='PRESENT')
    heure_arrivee = models.TimeField(null=True, blank=True)
    heure_depart = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('personnel', 'date')

    def __str__(self):
        return f"Présence {self.date} - {self.personnel.nom}: {self.statut}"

    @property
    def a_pointe_arrivee(self):
        if self.statut in ('ABSENT', 'CONGE'):
            return True
        return self.heure_arrivee is not None

    @property
    def a_pointe_depart(self):
        if self.statut in ('ABSENT', 'CONGE'):
            return True
        return self.heure_depart is not None

    @property
    def en_attente_depart(self):
        return (
            self.statut in ('PRESENT', 'RETARD')
            and self.heure_arrivee is not None
            and self.heure_depart is None
        )

class Paie(models.Model):
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('PAYE', 'Payé'),
        ('ANNULE', 'Annulé'),
    ]
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='paies')
    mois = models.IntegerField()
    annee = models.IntegerField()
    salaire_base = models.DecimalField(max_digits=12, decimal_places=2)
    primes = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    MODE_PAIEMENT_CHOICES = [
        ('ESPECES', 'Espèces'),
        ('VIREMENT', 'Virement'),
        ('CHEQUE', 'Chèque'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]
    net_a_payer = models.DecimalField(max_digits=12, decimal_places=2)
    devise = models.ForeignKey('finances.Devise', on_delete=models.PROTECT)
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT_CHOICES, default='ESPECES')
    reference_paiement = models.CharField(max_length=50, blank=True, null=True)
    statut_paiement = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    date_paiement = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Garantir un calcul compatible Decimal + Decimal (évite Decimal + float)
        self.primes = self.primes if self.primes is not None else 0
        self.deductions = self.deductions if self.deductions is not None else 0
        self.net_a_payer = self.salaire_base + self.primes - self.deductions
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Paie {self.mois}/{self.annee} - {self.personnel.nom}"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Paie)
def auto_post_salary_to_entries(sender, instance, created, **kwargs):
    if instance.statut_paiement == "PAYE":
        from finances.views import _hoada_auto_post_salary_to_entries
        try:
            _hoada_auto_post_salary_to_entries(instance)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error auto posting salary: {e}", exc_info=True)
