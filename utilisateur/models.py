from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
from inscription.models import Ecole, Eleve, Tuteur


class Utilisateur(AbstractUser):
    role_choices = [
        ('MANAGER', 'Manager'),
        ('DIRECTEUR', 'Directeur'),
        ('ENSEIGNANT', 'Enseignant'),
        ('TRESORIE', 'Trésorier'),
        ('PARENT', 'Parent'),
        ('ELEVE', 'Elève'),
        ('PROFESSEUR', 'Professeur'),
        ('CAISSIER', 'Caissier'),
    ]

    # Les trois profils ouverts à l'auto-inscription depuis la page publique.
    PROFIL_CHOICES = [
        ('PARENT', 'Parent'),
        ('ELEVE', 'Élève'),
        ('PROFESSEUR', 'Corps professoral'),
    ]

    # Rôles réservés au personnel administratif interne (créés via l'admin).
    ROLES_INTERNES = ('MANAGER', 'DIRECTEUR', 'TRESORIE', 'CAISSIER')

    prenom = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=role_choices, default='DIRECTEUR')
    avatar = models.ImageField(null=True, blank=True)
    ecole = models.ForeignKey(Ecole, on_delete=models.DO_NOTHING, null=True)

    # Rattachement du compte à la fiche métier déjà existante (créée par l'école).
    eleve = models.OneToOneField(
        Eleve, on_delete=models.SET_NULL, null=True, blank=True, related_name='compte_utilisateur'
    )
    tuteur = models.OneToOneField(
        Tuteur, on_delete=models.SET_NULL, null=True, blank=True, related_name='compte_utilisateur'
    )

    def __str__(self):
        return self.prenom

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.last_name}".strip() or self.username

    @property
    def is_parent(self):
        return self.role == 'PARENT'

    @property
    def is_eleve(self):
        return self.role == 'ELEVE'

    @property
    def is_caissier(self):
        """Compte rôle CAISSIER, ou fiche personnel GRH avec fonction Caissier."""
        if self.role == 'CAISSIER':
            return True
        from django.core.exceptions import ObjectDoesNotExist
        try:
            return self.personnel.fonction == 'Caissier'
        except ObjectDoesNotExist:
            return False

    @property
    def is_professeur(self):
        # Un caissier (même rattaché au corps professoral) n'est pas traité comme enseignant.
        if self.is_caissier:
            return False
        return self.role in ('PROFESSEUR', 'ENSEIGNANT')

    @property
    def is_personnel_interne(self):
        return self.role in self.ROLES_INTERNES


class Conversation(models.Model):
    """Fil de discussion parent ↔ professeur titulaire, autour d'un enfant inscrit."""

    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='conversations')
    inscription = models.ForeignKey(
        'inscription.Inscription', on_delete=models.CASCADE, related_name='conversations'
    )
    classe = models.ForeignKey(
        'inscription.Classe', on_delete=models.CASCADE, related_name='conversations'
    )
    annee_scolaire = models.ForeignKey(
        'inscription.Annee_Scolaire', on_delete=models.CASCADE, related_name='conversations'
    )
    sujet = models.CharField(max_length=200)
    parent = models.ForeignKey(
        'Utilisateur', on_delete=models.CASCADE, related_name='conversations_parent'
    )
    enseignant = models.ForeignKey(
        'Utilisateur', on_delete=models.CASCADE, related_name='conversations_enseignant'
    )
    cree_par = models.ForeignKey(
        'Utilisateur', on_delete=models.SET_NULL, null=True, related_name='conversations_creees'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_message_at', '-id']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'

    def __str__(self):
        return f"{self.sujet} — {self.inscription.eleve}"

    @property
    def eleve(self):
        return self.inscription.eleve


class MessageEchange(models.Model):
    """Message dans une conversation parent ↔ titulaire."""

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    auteur = models.ForeignKey(
        'Utilisateur', on_delete=models.CASCADE, related_name='messages_echanges'
    )
    contenu = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    lu_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at', 'id']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"{self.auteur} — {self.created_at:%d/%m/%Y %H:%M}"

    @property
    def est_lu(self):
        return self.lu_at is not None


class CommunicationDirection(models.Model):
    """Message de la direction vers les parents (ciblage flexible)."""

    CIBLE_PARENT = 'PARENT'
    CIBLE_CLASSE = 'CLASSE'
    CIBLE_SECTION = 'SECTION'
    CIBLE_ECOLE = 'ECOLE'
    CIBLE_CHOICES = [
        (CIBLE_PARENT, 'Un parent'),
        (CIBLE_CLASSE, 'Toute une classe'),
        (CIBLE_SECTION, 'Toute une section'),
        (CIBLE_ECOLE, "Toute l'école"),
    ]

    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='communications_direction')
    auteur = models.ForeignKey(
        'Utilisateur', on_delete=models.SET_NULL, null=True, related_name='communications_envoyees'
    )
    sujet = models.CharField(max_length=200)
    contenu = models.TextField()
    cible_type = models.CharField(max_length=20, choices=CIBLE_CHOICES, default=CIBLE_ECOLE)
    cible_parent = models.ForeignKey(
        'Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='communications_recues_directes',
        limit_choices_to={'role': 'PARENT'},
    )
    cible_classe = models.ForeignKey(
        'inscription.Classe', on_delete=models.SET_NULL, null=True, blank=True, related_name='communications_direction'
    )
    cible_section = models.ForeignKey(
        'inscription.Section', on_delete=models.SET_NULL, null=True, blank=True, related_name='communications_direction'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Communication direction'
        verbose_name_plural = 'Communications direction'

    def __str__(self):
        return f"{self.sujet} ({self.get_cible_type_display()})"

    @property
    def libelle_cible(self):
        if self.cible_type == self.CIBLE_PARENT and self.cible_parent_id:
            return f"Parent — {self.cible_parent.nom_complet}"
        if self.cible_type == self.CIBLE_CLASSE and self.cible_classe_id:
            return f"Classe — {self.cible_classe.classe}"
        if self.cible_type == self.CIBLE_SECTION and self.cible_section_id:
            return f"Section — {self.cible_section.section}"
        if self.cible_type == self.CIBLE_ECOLE:
            return f"École — {self.ecole.ecole}"
        return self.get_cible_type_display()


class CommunicationLecture(models.Model):
    """Destinataire parent d'une communication + suivi de lecture.

    Créé à l'envoi pour figer la liste des destinataires.
    `lu_at` reste null tant que le parent n'a pas ouvert le message.
    """

    communication = models.ForeignKey(
        CommunicationDirection, on_delete=models.CASCADE, related_name='lectures'
    )
    parent = models.ForeignKey(
        'Utilisateur', on_delete=models.CASCADE, related_name='lectures_communications'
    )
    lu_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('communication', 'parent')
        verbose_name = 'Destinataire / lecture'
        verbose_name_plural = 'Destinataires / lectures'

    @property
    def est_lu(self):
        return self.lu_at is not None
