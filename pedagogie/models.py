from django.db import models
from django.db.models import Avg

from grh.models import Personnel
from inscription.models import Ecole, Section, Classe, Annee_Scolaire, Inscription, Cycle


class Matiere(models.Model):
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)
    libelle = models.CharField(max_length=100)
    coefficient = models.DecimalField(max_digits=5, decimal_places=2)
    # Maxima d'une colonne « Trav. journ. » sur le bulletin officiel RDC (ex. 10, 20, 40…).
    maxima_periode = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=10,
        help_text="Points max TJ par période sur le bulletin. Examen de division = 2 × ce maxima.",
    )
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    # Enseignant « de référence » (surtout secondaire/humanités). Au primaire,
    # le titulaire de classe est utilisé par défaut sauf affectation spécifique.
    enserignant = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matieres_reference',
        verbose_name='Enseignant de référence',
    )

    class Meta:
        verbose_name = "Matière"
        verbose_name_plural = "Matières"
        unique_together = ("ecole", "section", "code")
        ordering = ["section__section", "libelle"]

    def __str__(self):
        return self.libelle

    @property
    def maxima_examen(self):
        """Maxima de la colonne EXAM. du trimestre/semestre (bulletin RDC)."""
        return self.maxima_periode * 2

    @property
    def maxima_division(self):
        """Tot. d'une division = TJ1 + TJ2 + EXAM = 4 × maxima_periode."""
        return self.maxima_periode * 4

    def enseignant_pour_classe(self, classe):
        """Enseignant effectif pour cette matière dans une classe.

        Priorité :
        1. Affectation spécifique (classe + matière)
        2. Titulaire de la classe si cycle PRIMAIRE / MATERNELLE
        3. Enseignant de référence de la matière
        """
        aff = (
            AffectationEnseignement.objects
            .filter(classe=classe, matiere=self)
            .select_related('enseignant')
            .first()
        )
        if aff:
            return aff.enseignant
        cycle = getattr(getattr(classe.section, 'cycle', None), 'cycle', '') or ''
        if cycle in ('PRIMAIRE', 'MATERNELLE') and classe.titulaire_id:
            return classe.titulaire
        return self.enserignant


class AffectationEnseignement(models.Model):
    """Professeur affecté à une matière pour une classe donnée.

    Au primaire, sans affectation le titulaire assure toutes les matières.
    Une affectation permet d'attribuer un cours à un autre enseignant.
    """

    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='affectations_enseignement')
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='affectations_matieres')
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='affectations_classes')
    enseignant = models.ForeignKey(
        Personnel,
        on_delete=models.CASCADE,
        related_name='affectations_cours',
        verbose_name='Professeur du cours',
    )

    class Meta:
        verbose_name = 'Affectation enseignant (cours)'
        verbose_name_plural = 'Affectations enseignants (cours)'
        unique_together = ('classe', 'matiere')
        ordering = ['classe__classe', 'matiere__libelle']

    def __str__(self):
        return f"{self.matiere.libelle} — {self.classe.classe} → {self.enseignant}"


class DivisionAnnee(models.Model):
    """Trimestre (maternelle/primaire) ou semestre (CTEB/humanites) du bulletin RDC."""

    TYPE_CHOICES = [
        ('TRIMESTRE', 'Trimestre'),
        ('SEMESTRE', 'Semestre'),
    ]

    annee_scolaire = models.ForeignKey(
        Annee_Scolaire, on_delete=models.CASCADE, related_name='divisions_bulletin'
    )
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='divisions_bulletin')
    type_division = models.CharField(max_length=20, choices=TYPE_CHOICES)
    numero = models.PositiveSmallIntegerField()
    libelle = models.CharField(max_length=60)
    date_debut = models.DateField()
    date_fin = models.DateField()
    est_encours = models.BooleanField(
        default=False,
        verbose_name='En cours',
        help_text='Trimestre ou semestre actuellement actif. Désactivé automatiquement après la date de fin.',
    )

    class Meta:
        verbose_name = 'Division annee (trimestre/semestre)'
        verbose_name_plural = 'Divisions annee (trimestres/semestres)'
        unique_together = ('annee_scolaire', 'cycle', 'type_division', 'numero')
        ordering = ['annee_scolaire', 'cycle__cycle', 'numero']

    def __str__(self):
        return f"{self.libelle} — {self.cycle.cycle} ({self.annee_scolaire})"

    def est_expire(self, aujourdhui=None):
        from datetime import date as _date
        jour = aujourdhui or _date.today()
        return self.date_fin < jour

    def couvre_date(self, aujourdhui=None):
        from datetime import date as _date
        jour = aujourdhui or _date.today()
        return self.date_debut <= jour <= self.date_fin


class PeriodeBulletin(models.Model):
    """Periode d'evaluation telle qu'elle apparait sur le bulletin scolaire RDC."""

    annee_scolaire = models.ForeignKey(
        Annee_Scolaire, on_delete=models.CASCADE, related_name='periodes_bulletin'
    )
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='periodes_bulletin')
    division = models.ForeignKey(
        DivisionAnnee, on_delete=models.CASCADE, related_name='periodes'
    )
    numero = models.PositiveSmallIntegerField(
        help_text="Numero sur le bulletin (1 a 6 en trimestriel, 1 a 4 en semestriel)."
    )
    libelle = models.CharField(max_length=60)
    date_debut = models.DateField()
    date_fin = models.DateField()
    est_encours = models.BooleanField(
        default=False,
        verbose_name='En cours',
        help_text='Période bulletin actuellement active. Désactivée automatiquement après la date de fin.',
    )

    class Meta:
        verbose_name = 'Periode bulletin'
        verbose_name_plural = 'Periodes bulletin'
        unique_together = ('annee_scolaire', 'cycle', 'numero')
        ordering = ['annee_scolaire', 'cycle__cycle', 'numero']

    def __str__(self):
        return f"{self.libelle} — {self.cycle.cycle} ({self.annee_scolaire})"

    def est_expire(self, aujourdhui=None):
        from datetime import date as _date
        jour = aujourdhui or _date.today()
        return self.date_fin < jour

    def couvre_date(self, aujourdhui=None):
        from datetime import date as _date
        jour = aujourdhui or _date.today()
        return self.date_debut <= jour <= self.date_fin

    @classmethod
    def pour_section(cls, section, annee_scolaire):
        """Periodes applicables a une section (selon son cycle)."""
        return cls.objects.filter(
            annee_scolaire=annee_scolaire,
            cycle=section.cycle,
        ).select_related('division')


class TravailCote(models.Model):
    """Travail coté alimentant le bulletin RDC.

    Lien officiel bulletin MEPST :
    - Travaux journaliers (TJ) → colonne de la période (1ère–6ème / 1ère–4ème)
    - Examen de division → colonne EXAM. du trimestre ou du semestre
    - Tot. division = TJ(période A) + TJ(période B) + EXAM.
    """

    TYPE_CHOICES = [
        ("DEVOIR", "Devoir"),
        ("INTERROGATION", "Interrogation"),
        ("EXAMEN", "Examen"),
        ("COMPOSITION", "Composition"),
        ("TP", "Travail pratique"),
        ("AUTRE", "Autre"),
    ]
    ROLE_BULLETIN_CHOICES = [
        ("TJ", "Travaux journaliers (période)"),
        ("EXAMEN", "Examen (trimestre / semestre)"),
    ]
    TYPES_EXAMEN = frozenset({"EXAMEN", "COMPOSITION"})

    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name="travaux_cotes")
    annee_scolaire = models.ForeignKey(
        Annee_Scolaire, on_delete=models.CASCADE, related_name="travaux_cotes"
    )
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name="travaux_cotes")
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name="travaux_cotes")
    role_bulletin = models.CharField(
        max_length=10,
        choices=ROLE_BULLETIN_CHOICES,
        default="TJ",
        verbose_name="Rôle sur le bulletin",
        help_text="TJ = note de période ; EXAMEN = examen de trimestre/semestre.",
    )
    periode = models.ForeignKey(
        'PeriodeBulletin',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='travaux_cotes',
        verbose_name='Période bulletin (TJ)',
        help_text="Obligatoire pour les travaux journaliers.",
    )
    division = models.ForeignKey(
        'DivisionAnnee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='examens',
        verbose_name='Trimestre / semestre (examen)',
        help_text="Obligatoire pour un examen de division.",
    )
    type_travail = models.CharField(max_length=20, choices=TYPE_CHOICES, default="DEVOIR")
    titre = models.CharField(max_length=150, blank=True, default="")
    date_travail = models.DateField()
    bareme = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    coefficient = models.DecimalField(max_digits=5, decimal_places=2, default=1)

    class Meta:
        verbose_name = "Travail coté"
        verbose_name_plural = "Travaux cotés"
        ordering = ["-date_travail", "-id"]

    def __str__(self):
        libelle = self.titre or self.get_type_travail_display()
        return f"{libelle} — {self.matiere.libelle} ({self.classe.classe})"

    @classmethod
    def role_depuis_type(cls, type_travail):
        return "EXAMEN" if type_travail in cls.TYPES_EXAMEN else "TJ"

    def synchroniser_role_bulletin(self):
        """Aligne role_bulletin / division sur le type et la période."""
        if not self.role_bulletin:
            self.role_bulletin = self.role_depuis_type(self.type_travail)
        if self.role_bulletin == "TJ":
            if self.periode_id and not self.division_id:
                self.division_id = self.periode.division_id
        elif self.role_bulletin == "EXAMEN":
            self.periode = None

    @property
    def nb_notes_saisies(self):
        return self.notes.exclude(note__isnull=True).count()

    @property
    def nb_eleves_attendus(self):
        return Inscription.objects.filter(classe=self.classe, annee_s=self.annee_scolaire).count()

    @property
    def moyenne(self):
        return self.notes.exclude(note__isnull=True).aggregate(m=Avg("note"))["m"]

    @property
    def est_complet(self):
        attendus = self.nb_eleves_attendus
        return attendus > 0 and self.nb_notes_saisies >= attendus

    def save(self, *args, **kwargs):
        if self.type_travail in self.TYPES_EXAMEN:
            self.role_bulletin = "EXAMEN"
        elif not self.role_bulletin:
            self.role_bulletin = "TJ"

        if self.role_bulletin == "EXAMEN":
            self.periode = None
        elif self.role_bulletin == "TJ" and self.periode_id and not self.division_id:
            # Evite requete si periode deja chargee
            try:
                self.division_id = self.periode.division_id
            except Exception:
                pass
        super().save(*args, **kwargs)


class NoteEleve(models.Model):
    travail = models.ForeignKey(TravailCote, on_delete=models.CASCADE, related_name="notes")
    inscription = models.ForeignKey(
        Inscription, on_delete=models.CASCADE, related_name="notes_travaux"
    )
    note = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    absent = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        unique_together = ("travail", "inscription")
        ordering = ["inscription__eleve__nom", "inscription__eleve__prenom"]

    def __str__(self):
        valeur = "Absent" if self.absent else self.note
        return f"{self.inscription.eleve} — {valeur}"

    @property
    def est_verrouillee(self):
        """Une note donnee (valeur ou absence) ne peut plus etre modifiee."""
        return self.absent or self.note is not None

    @property
    def sur_20(self):
        if self.note is None or not self.travail.bareme:
            return None
        return round((self.note / self.travail.bareme) * 20, 2)

    def save(self, *args, **kwargs):
        if self.pk:
            ancienne = (
                NoteEleve.objects.filter(pk=self.pk)
                .only('note', 'absent')
                .first()
            )
            if (
                ancienne
                and (ancienne.absent or ancienne.note is not None)
                and (ancienne.note != self.note or ancienne.absent != self.absent)
            ):
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    "Cette note est verrouillee et ne peut plus etre modifiee."
                )
        super().save(*args, **kwargs)


class PresenceClasse(models.Model):
    """Appel quotidien d'une classe pour une date donnée."""

    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='presences_classes')
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='presences_quotidiennes')
    annee_scolaire = models.ForeignKey(
        Annee_Scolaire, on_delete=models.CASCADE, related_name='presences_classes'
    )
    date = models.DateField()
    saisi_par = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presences_classes_saisies',
    )
    remarque = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Présence de classe'
        verbose_name_plural = 'Présences de classe'
        unique_together = ('classe', 'date')
        ordering = ['-date', 'classe__classe']

    def __str__(self):
        return f"Présence {self.classe.classe} — {self.date}"

    @property
    def nb_presents(self):
        return self.lignes.filter(statut='PRESENT').count()

    @property
    def nb_absents(self):
        return self.lignes.filter(statut='ABSENT').count()

    @property
    def nb_retards(self):
        return self.lignes.filter(statut='RETARD').count()

    @property
    def nb_excuses(self):
        return self.lignes.filter(statut='EXCUSE').count()


class PresenceEleve(models.Model):
    """Statut de présence d'un élève pour un appel quotidien."""

    STATUT_CHOICES = [
        ('PRESENT', 'Présent'),
        ('ABSENT', 'Absent'),
        ('RETARD', 'Retard'),
        ('EXCUSE', 'Excusé'),
    ]

    presence_classe = models.ForeignKey(
        PresenceClasse, on_delete=models.CASCADE, related_name='lignes'
    )
    inscription = models.ForeignKey(
        Inscription, on_delete=models.CASCADE, related_name='presences_quotidiennes'
    )
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='PRESENT')
    commentaire = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        verbose_name = 'Présence élève'
        verbose_name_plural = 'Présences élèves'
        unique_together = ('presence_classe', 'inscription')
        ordering = ['inscription__eleve__nom', 'inscription__eleve__prenom']

    def __str__(self):
        return f"{self.inscription.eleve} — {self.get_statut_display()} ({self.presence_classe.date})"



class BulletinEleve(models.Model):
    """Bulletin scolaire RDC lie a une inscription (un eleve / annee / classe).

    Cree a l'inscription et recalcule automatiquement a chaque saisie de notes.
    """

    inscription = models.OneToOneField(
        Inscription,
        on_delete=models.CASCADE,
        related_name='bulletin',
        verbose_name='Inscription / eleve',
    )
    ecole = models.ForeignKey(
        Ecole, on_delete=models.CASCADE, related_name='bulletins_eleves'
    )
    total_obtenus = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='Total general obtenu'
    )
    total_maxima = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='Maxima generaux'
    )
    pourcentage = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Pourcentage'
    )
    snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bulletin eleve'
        verbose_name_plural = 'Bulletins eleves'
        ordering = ['-updated_at']

    def __str__(self):
        eleve = self.inscription.eleve
        pct = f'{self.pourcentage} %' if self.pourcentage is not None else '—'
        return f'Bulletin {eleve} — {pct}'

    @property
    def est_vide(self):
        return not self.total_obtenus or self.total_obtenus == 0


class CoursEnLigne(models.Model):
    """Cours numérique organisé par un enseignant pour une classe / matière."""

    NIVEAU_CHOICES = [
        ('DEBUTANT', 'Débutant'),
        ('INTERMEDIAIRE', 'Intermédiaire'),
        ('AVANCE', 'Avancé'),
    ]

    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='cours_en_ligne')
    annee_scolaire = models.ForeignKey(
        Annee_Scolaire, on_delete=models.CASCADE, related_name='cours_en_ligne'
    )
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='cours_en_ligne')
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='cours_en_ligne')
    enseignant = models.ForeignKey(
        Personnel,
        on_delete=models.CASCADE,
        related_name='cours_en_ligne',
        verbose_name='Auteur',
    )
    titre = models.CharField(max_length=200)
    sous_titre = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Sous-titre',
        help_text='Phrase d’accroche visible sous le titre (style LinkedIn Learning).',
    )
    description = models.TextField(
        blank=True,
        verbose_name='À propos du cours',
        help_text='Présentation détaillée du cours.',
    )
    objectifs = models.TextField(
        blank=True,
        verbose_name='Ce que vous allez apprendre',
        help_text='Un objectif par ligne.',
    )
    competences = models.CharField(
        max_length=400,
        blank=True,
        verbose_name='Compétences',
        help_text='Séparées par des virgules (ex: Fractions, Calcul mental).',
    )
    prerequis = models.TextField(
        blank=True,
        verbose_name='Prérequis',
        help_text='Ce que l’élève doit déjà savoir.',
    )
    public_cible = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Public cible',
        help_text='Ex: Élèves de 5e année primaire',
    )
    niveau = models.CharField(
        max_length=20,
        choices=NIVEAU_CHOICES,
        default='DEBUTANT',
        verbose_name='Niveau',
    )
    duree_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='Durée estimée (min)',
        help_text='0 = calcul automatique à partir des leçons.',
    )
    image_couverture = models.ImageField(
        upload_to='cours_couvertures/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Image de couverture',
    )
    publie = models.BooleanField(
        default=False,
        verbose_name='Publié en ligne',
        help_text='Visible par les élèves de la classe une fois publié.',
    )
    date_publication = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cours en ligne'
        verbose_name_plural = 'Cours en ligne'
        ordering = ['matiere__libelle', 'titre']

    def __str__(self):
        return f'{self.titre} ({self.matiere.libelle} — {self.classe.classe})'

    @property
    def nb_lecons(self):
        return LeconEnLigne.objects.filter(chapitre__cours=self).count()

    @property
    def nb_lecons_publiees(self):
        return LeconEnLigne.objects.filter(
            chapitre__cours=self, publie=True, chapitre__publie=True
        ).count()

    def liste_objectifs(self):
        return [l.strip() for l in (self.objectifs or '').splitlines() if l.strip()]

    def liste_competences(self):
        return [c.strip() for c in (self.competences or '').split(',') if c.strip()]

    def duree_effective_minutes(self):
        if self.duree_minutes:
            return self.duree_minutes
        total = LeconEnLigne.objects.filter(
            chapitre__cours=self, publie=True, chapitre__publie=True
        ).aggregate(s=models.Sum('duree_minutes'))['s']
        return total or 0

    def duree_affichee(self):
        minutes = self.duree_effective_minutes()
        if not minutes:
            return '—'
        if minutes < 60:
            return f'{minutes} min'
        h, m = divmod(minutes, 60)
        return f'{h} h {m:02d}' if m else f'{h} h'

    def structure_pedagogique(self, publie_only=False):
        """Retourne [(chapitre, [sous_chapitres…]), …] ordonnés."""
        chap_qs = self.chapitres.all().order_by('ordre', 'id')
        if publie_only:
            chap_qs = chap_qs.filter(publie=True)
        rows = []
        for chapitre in chap_qs:
            sous_qs = chapitre.sous_chapitres.all().order_by('ordre', 'id')
            if publie_only:
                sous_qs = sous_qs.filter(publie=True)
            rows.append((chapitre, list(sous_qs)))
        return rows


class ChapitreCours(models.Model):
    """Chapitre d'un cours en ligne (peut contenir des sous-chapitres / leçons)."""

    cours = models.ForeignKey(CoursEnLigne, on_delete=models.CASCADE, related_name='chapitres')
    titre = models.CharField(max_length=200)
    resume = models.CharField(max_length=300, blank=True, verbose_name='Résumé')
    contenu = models.TextField(
        blank=True,
        verbose_name='Introduction du chapitre',
        help_text='Texte d’introduction du chapitre (optionnel).',
    )
    video_url = models.URLField(
        blank=True,
        verbose_name='Vidéo du chapitre',
        help_text='Lien YouTube / Vimeo pour ce chapitre.',
    )
    image = models.ImageField(
        upload_to='cours_chapitres/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Image du chapitre',
    )
    ordre = models.PositiveSmallIntegerField(default=1)
    publie = models.BooleanField(default=True, verbose_name='Chapitre visible')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Chapitre de cours'
        verbose_name_plural = 'Chapitres de cours'
        ordering = ['ordre', 'id']

    def __str__(self):
        return f'Ch. {self.ordre} — {self.titre}'

    @property
    def nb_sous_chapitres(self):
        return self.sous_chapitres.count()


class LeconEnLigne(models.Model):
    """Sous-chapitre / leçon rattachée à un chapitre."""

    TYPE_CHOICES = [
        ('VIDEO', 'Vidéo'),
        ('LECTURE', 'Lecture'),
        ('DOCUMENT', 'Document'),
        ('EXERCICE', 'Exercice'),
    ]

    cours = models.ForeignKey(
        CoursEnLigne, on_delete=models.CASCADE, related_name='lecons',
        null=True, blank=True,
    )
    chapitre = models.ForeignKey(
        ChapitreCours,
        on_delete=models.CASCADE,
        related_name='sous_chapitres',
        null=True,
        blank=True,
        verbose_name='Chapitre',
    )
    titre = models.CharField(max_length=200)
    resume = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Résumé',
        help_text='Courte description affichée dans le programme du cours.',
    )
    type_contenu = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='LECTURE',
        verbose_name='Type',
    )
    contenu = models.TextField(
        blank=True,
        help_text='Texte du cours (explications, exercices, consignes…).',
    )
    video_url = models.URLField(
        blank=True,
        verbose_name='Lien vidéo',
        help_text='Lien YouTube, Vimeo ou autre (optionnel).',
    )
    image = models.ImageField(
        upload_to='cours_sous_chapitres/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Image',
    )
    fichier = models.FileField(
        upload_to='cours_en_ligne/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Fichier joint',
        help_text='PDF ou document (optionnel).',
    )
    duree_minutes = models.PositiveIntegerField(
        default=5,
        verbose_name='Durée (min)',
    )
    ordre = models.PositiveSmallIntegerField(default=1)
    publie = models.BooleanField(
        default=True,
        verbose_name='Sous-chapitre visible',
        help_text='Décochez pour garder un brouillon non visible aux élèves.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sous-chapitre / leçon'
        verbose_name_plural = 'Sous-chapitres / leçons'
        ordering = ['ordre', 'id']

    def __str__(self):
        return f'{self.ordre}. {self.titre}'

    def save(self, *args, **kwargs):
        if self.chapitre_id:
            self.cours_id = self.chapitre.cours_id
        super().save(*args, **kwargs)

    def duree_affichee(self):
        m = self.duree_minutes or 0
        if not m:
            return '—'
        if m < 60:
            return f'{m} min'
        h, rest = divmod(m, 60)
        return f'{h} h {rest:02d}' if rest else f'{h} h'


class ProgressionLecon(models.Model):
    """Suivi de progression d'un élève sur une leçon."""

    inscription = models.ForeignKey(
        Inscription, on_delete=models.CASCADE, related_name='progressions_lecons'
    )
    lecon = models.ForeignKey(
        LeconEnLigne, on_delete=models.CASCADE, related_name='progressions'
    )
    vue = models.BooleanField(default=True)
    terminee = models.BooleanField(default=False)
    vue_at = models.DateTimeField(auto_now_add=True)
    terminee_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Progression leçon'
        verbose_name_plural = 'Progressions leçons'
        unique_together = ('inscription', 'lecon')

    def __str__(self):
        return f'{self.inscription} — {self.lecon}'
