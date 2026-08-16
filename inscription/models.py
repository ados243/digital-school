from django.db import models

# Create your models here.


class Commune(models.Model):
    commune = models.CharField(max_length=200)
    def __str__(self):
        return self.commune

class Quartier(models.Model):
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    quartier = models.CharField(max_length=100)

    def __str__(self):
        return self.quartier

class Ecole(models.Model):
    type_ecole_choices = [
        ('PUBLICQUE', 'Publique'),
        ('PRIVEE', 'Privée'),
        ('CONVENTIONNEE', 'Conventionnée')
    ]
    code_ecole = models.CharField(max_length=20)
    ecole = models.CharField(max_length=150)
    type_ecole = models.CharField(max_length=20, choices=type_ecole_choices, default='PRIVEE')
    quartier = models.ForeignKey(Quartier, on_delete=models.DO_NOTHING)
    adresse = models.CharField(max_length=200)
    telephone1 = models.CharField(max_length=15)
    telephone2 = models.CharField(max_length=15)
    email = models.EmailField()
    activation = models.BooleanField(default=False)

    def __str__(self):
        return self.ecole

class Annee_Scolaire(models.Model):
    """Année scolaire nationale (calendrier MINEDU-NC / EPSP), partagée par toutes les écoles."""

    anne_scolaire = models.CharField(
        max_length=9,
        unique=True,
        verbose_name='Année scolaire',
        help_text='Libellé national, ex. 2025-2026',
    )
    date_debut = models.DateField(verbose_name='Date de début')
    date_fin = models.DateField(verbose_name='Date de fin')
    est_encoure = models.BooleanField(
        default=False,
        verbose_name='Année en cours',
        help_text='Une seule année nationale peut être marquée en cours.',
    )

    class Meta:
        verbose_name = 'Année scolaire'
        verbose_name_plural = 'Années scolaires'
        ordering = ['-est_encoure', '-anne_scolaire']

    def __str__(self):
        return self.anne_scolaire

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.est_encoure:
            type(self).objects.exclude(pk=self.pk).filter(est_encoure=True).update(
                est_encoure=False
            )

class Cycle(models.Model):
    cycle_choices = [
        ('MATERNELLE', 'Maternelle'),
        ('PRIMAIRE', 'Primaire'),
        ('SECONDAIRE', 'Secondaire'),
        ('HUMANITE','Humanite')
    ]

    cycle = models.CharField(max_length=10, choices=cycle_choices, default='Primaire', unique=True)

    def __str__(self):
        return self.cycle

class Section(models.Model):
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    section = models.CharField(max_length=50,unique=True)

    def __str__(self):
        return self.section

class Classe(models.Model):
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    classe = models.CharField(max_length=10)
    capacite_max = models.IntegerField()
    salle = models.CharField(max_length=10)
    # Enseignant titulaire de la salle de classe (optionnel).
    titulaire = models.ForeignKey(
        'grh.Personnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes_titulaires',
        verbose_name='Enseignant titulaire',
    )

    class Meta:
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        unique_together = ("ecole", "section", "classe")

    def __str__(self):
        return self.classe

    def annee_en_cours(self):
        return Annee_Scolaire.objects.filter(est_encoure=True).first()

    def inscrits_annee_en_cours(self, annee=None):
        annee = annee or self.annee_en_cours()
        if not annee:
            return 0
        return Inscription.objects.filter(classe=self, annee_s=annee).count()

    @property
    def taux_remplissage(self):
        if self.capacite_max <= 0:
            return 0
        return int((self.inscrits_annee_en_cours() / self.capacite_max) * 100)

    @property
    def est_complete(self):
        return self.inscrits_annee_en_cours() >= self.capacite_max

class Tuteur(models.Model):
    lien_parente_choice= [
        ('PERE','Pére'),
        ('MERE','Mère'),
        ('TITEUR','Titeur'),
        ('AUTRE', 'Autre')

    ]
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=10)
    nom = models.CharField(max_length=250)
    Post_nom = models.CharField(max_length=250)
    prenom = models.CharField(max_length=250)
    lien_parente = models.CharField(max_length=25, choices=lien_parente_choice, default='pere')
    telephone = models.CharField(max_length=14)
    telephone2 = models.CharField(max_length=14, null= True, blank=True)
    email = models.EmailField(null=True, blank=True)
    quartier = models.ForeignKey(
        Quartier,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name="Quartier de résidence",
    )
    adresse = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Adresse de résidence",
    )

    class Meta:
        verbose_name = "Tuteur"
        verbose_name_plural = "Tuteurs"
        unique_together = ("ecole", "matricule")

    def generer_matricule(self):
        """Matricule séquentiel du type TUT-000001, propre à chaque école."""
        prefixe = "TUT-"
        dernier = (
            Tuteur.objects.filter(ecole=self.ecole, matricule__startswith=prefixe)
            .order_by("matricule")
            .last()
        )
        sequence = 0
        if dernier:
            try:
                sequence = int(dernier.matricule[len(prefixe):])
            except ValueError:
                sequence = Tuteur.objects.filter(ecole=self.ecole).count()
        return f"{prefixe}{sequence + 1:06d}"

    def save(self, *args, **kwargs):
        if not self.matricule and self.ecole_id:
            self.matricule = self.generer_matricule()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

class Eleve(models.Model):
        Sexe_choices = [
            ('Masculin', 'M'),
            ('Feminin', 'F'),
        ]
        ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE)
        matricule = models.CharField(max_length=10, unique=True)
        nom = models.CharField(max_length=250)
        Post_nom = models.CharField(max_length=250)
        prenom = models.CharField(max_length=250)
        titeur = models.ForeignKey(Tuteur, on_delete=models.CASCADE)
        sexe = models.CharField(max_length=20, choices=Sexe_choices)
        date_de_naissance = models.DateField()
        nationalite = models.CharField(max_length=50, default="Congolaise")
        photo = models.ImageField(null=True, blank=True)

        class Meta:
            verbose_name = "Élève"
            verbose_name_plural = "Élèves"

        def generer_matricule(self):
            """Matricule séquentiel du type ELV-000001, unique dans toute l'application."""
            prefixe = "ELV-"
            dernier = (
                Eleve.objects.filter(matricule__startswith=prefixe)
                .order_by("matricule")
                .last()
            )
            sequence = 0
            if dernier:
                try:
                    sequence = int(dernier.matricule[len(prefixe):])
                except ValueError:
                    sequence = Eleve.objects.count()
            return f"{prefixe}{sequence + 1:06d}"

        def save(self, *args, **kwargs):
            if not self.matricule and self.ecole_id:
                self.matricule = self.generer_matricule()
            super().save(*args, **kwargs)

        def __str__(self):
            return f"{self.nom} {self.prenom}"


class Inscription(models.Model):
    type_inscription_choices = [
        ('NOUVELLE', 'Nouvelle'),
        ('REINSCRIPTION', 'Reinscription'),
        ('TRANSFERT', 'Transfert'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.DO_NOTHING)
    classe = models.ForeignKey(Classe, on_delete=models.DO_NOTHING)
    annee_s = models.ForeignKey(Annee_Scolaire, on_delete=models.DO_NOTHING)
    numero_ins = models.CharField(max_length=20)
    date= models.DateField(auto_now_add=True)
    type_iscription = models.CharField(max_length=20, choices=type_inscription_choices, default='NOUVELLE')
    frais_inscription = models.BooleanField(default=False)

    def generer_numero(self):
        """Numéro séquentiel du type INS-2026-2027-0001, remis à zéro à chaque année scolaire."""
        prefixe = f"INS-{self.annee_s.anne_scolaire}-"
        dernier = (
            Inscription.objects.filter(annee_s=self.annee_s, numero_ins__startswith=prefixe)
            .order_by("numero_ins")
            .last()
        )
        sequence = 0
        if dernier:
            try:
                sequence = int(dernier.numero_ins[len(prefixe):])
            except ValueError:
                sequence = Inscription.objects.filter(annee_s=self.annee_s).count()
        return f"{prefixe}{sequence + 1:04d}"

    def save(self, *args, **kwargs):
        if not self.numero_ins and self.annee_s_id:
            self.numero_ins = self.generer_numero()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.eleve.nom} {self.eleve.prenom}"