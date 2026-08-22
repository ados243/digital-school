from django.db import models
from inscription.models import Ecole, Annee_Scolaire, Classe, Inscription, Section


# Create your models here.

class TypeFrais(models.Model):
    ecole = models.ForeignKey(Ecole, on_delete=models.DO_NOTHING)
    libelle = models.CharField(max_length=255)
    description = models.CharField(max_length=500)
    def __str__(self):
        return self.libelle

class Devise(models.Model):
    devise_choices = [
        ('CDF', 'CDF'),
        ('USD', 'USD'),
    ]
    devise = models.CharField(max_length=5, choices=devise_choices, default='USD')

    def __str__(self):
        return self.devise


class TauxChange(models.Model):
    """
    Taux de conversion CDF ↔ USD saisi manuellement par établissement.
    Convention RDC : `taux` = nombre de francs congolais pour 1 dollar américain.
    Exemple : 2850 signifie 1 USD = 2 850 CDF.
    """

    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name="taux_change")
    taux = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        help_text="Nombre de CDF pour 1 USD",
    )
    date_effet = models.DateField()
    date_saisie = models.DateTimeField(auto_now_add=True)
    saisi_par = models.CharField(max_length=80, blank=True)
    commentaire = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date_effet", "-date_saisie"]
        verbose_name = "Taux de change"
        verbose_name_plural = "Taux de change"

    def __str__(self):
        return f"1 USD = {self.taux} CDF ({self.date_effet})"

    @classmethod
    def courant_pour_ecole(cls, ecole, a_la_date=None):
        """Retourne le taux le plus récent applicable pour l'école."""
        if ecole is None:
            return None
        from django.utils import timezone

        jour = a_la_date or timezone.localdate()
        return (
            cls.objects.filter(ecole=ecole, date_effet__lte=jour)
            .order_by("-date_effet", "-date_saisie")
            .first()
        )


class Frais_Scolaire(models.Model):

    type_frais = models.ForeignKey(TypeFrais, on_delete=models.CASCADE)
    annee = models.ForeignKey(Annee_Scolaire, on_delete=models.CASCADE)
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Barème pour toute la section. Laisser vide si le frais vise des classes précises.",
    )
    classes = models.ManyToManyField(
        Classe,
        through="FraisClasse",
        related_name="frais_scolaires",
        blank=True,
    )
    montant = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    devise = models.ForeignKey(Devise, on_delete=models.CASCADE)
    echeance = models.DateField()
    est_obligatoire = models.BooleanField(default=True)

    def __str__(self):
        if self.section_id:
            return f"{self.type_frais} - {self.section} ({self.annee})"
        return f"{self.type_frais} — classes ciblées ({self.annee})"

    def est_specifique(self):
        cache = getattr(self, "_prefetched_objects_cache", None)
        if cache is not None and "classes" in cache:
            return bool(self.classes.all())
        return self.classes.exists()

    def portee_libelle(self):
        if self.est_specifique():
            noms = [str(c.classe) for c in self.classes.all()]
            return ", ".join(noms) if noms else "Classes ciblées"
        return str(self.section) if self.section_id else "—"


class FraisClasse(models.Model):
    """Affectation d'un frais à une classe (frais spécifique, une ou plusieurs classes)."""

    frais = models.ForeignKey(
        Frais_Scolaire,
        on_delete=models.CASCADE,
        related_name="affectations_classe",
    )
    classe = models.ForeignKey(
        Classe,
        on_delete=models.CASCADE,
        related_name="affectations_frais",
    )

    class Meta:
        verbose_name = "Frais par classe"
        verbose_name_plural = "Frais par classe"
        constraints = [
            models.UniqueConstraint(
                fields=["frais", "classe"],
                name="uniq_frais_classe",
            )
        ]

    def __str__(self):
        return f"{self.frais.type_frais} → {self.classe}"


class Paiement(models.Model):
    mode_paiement_choices = [
        ('ESPECES', 'ESPECE'),
        ('MOBILE_MONEY', 'MOBILE_MONEY'),
        ('VIREMENT', 'VIREMENT'),
        ('CHEQUE', 'CHEQUE'),
    ]
    statut_choices = [
        ('VALIDE', 'VALIDE'),
        ('ANNULE', 'ANNULE'),
        ('EN_ATTENTE', 'EN_ATTENTE'),
    ]

    eleve = models.ForeignKey(Inscription, on_delete=models.CASCADE)
    frais = models.ForeignKey(Frais_Scolaire, on_delete=models.CASCADE)
    numero_recu = models.CharField(max_length=16)
    montant_paye = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    devise = models.ForeignKey(Devise, on_delete=models.CASCADE)
    # Conversion manuelle CDF ↔ USD (snapshot au moment de l'encaissement)
    taux_change = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Taux appliqué : CDF pour 1 USD",
    )
    montant_origine = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Montant réellement reçu avant conversion",
    )
    devise_origine = models.ForeignKey(
        Devise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paiements_origine",
        help_text="Devise réellement encaissée (si différente du frais)",
    )
    mode_paiement = models.CharField(max_length=12, choices=mode_paiement_choices, default='ESPECES')
    reference_trans = models.CharField(max_length=25, null=True)
    date_encodage = models.DateTimeField(auto_now_add=True)
    caissier = models.CharField(max_length=30)
    statut = models.CharField(max_length=20, choices=statut_choices, default='EN_ATTENTE')

    def __str__(self):
        return str(f"{self.numero_recu} - {self.eleve}")


class DemandeModificationPaiement(models.Model):
    """Demande du caissier pour corriger un paiement mal saisi — traitée par l'admin."""

    STATUT_CHOICES = [
        ("EN_ATTENTE", "En attente"),
        ("TRAITEE", "Traitée"),
        ("REJETEE", "Rejetée"),
    ]

    paiement = models.ForeignKey(
        Paiement,
        on_delete=models.CASCADE,
        related_name="demandes_modification",
    )
    motif = models.TextField(verbose_name="Motif de la demande")
    demande_par = models.CharField(max_length=80)
    date_demande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="EN_ATTENTE")
    traite_par = models.CharField(max_length=80, blank=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    reponse_admin = models.TextField(blank=True, verbose_name="Réponse de l'admin")

    class Meta:
        ordering = ["-date_demande"]
        verbose_name = "Demande de modification de paiement"
        verbose_name_plural = "Demandes de modification de paiement"

    def __str__(self):
        return f"Demande #{self.pk} — {self.paiement.numero_recu} ({self.statut})"

    @classmethod
    def ouverte_pour_paiement(cls, paiement):
        return cls.objects.filter(paiement=paiement, statut="EN_ATTENTE").first()


class ClotureCaisse(models.Model):
    """Clôture de journée du caissier — fige les indicateurs de la journée."""

    ecole = models.ForeignKey(
        Ecole, on_delete=models.CASCADE, related_name="clotures_caisse"
    )
    date_journee = models.DateField(verbose_name="Journée")
    caissier = models.CharField(max_length=80)
    date_cloture = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)

    nb_paiements = models.PositiveIntegerField(default=0)
    nb_eleves = models.PositiveIntegerField(default=0)
    total_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_cdf = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_especes_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_especes_cdf = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_mobile_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_mobile_cdf = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_autres_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_autres_cdf = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        ordering = ["-date_journee", "-date_cloture"]
        verbose_name = "Clôture de caisse"
        verbose_name_plural = "Clôtures de caisse"
        constraints = [
            models.UniqueConstraint(
                fields=["ecole", "date_journee", "caissier"],
                name="uniq_cloture_caisse_ecole_jour_caissier",
            )
        ]

    def __str__(self):
        return f"Clôture {self.date_journee} — {self.caissier} ({self.ecole})"


class BudgetAnnuel(models.Model):
    """Budget figé pour une année scolaire (rubriques + détail minerval par classe)."""

    ecole = models.ForeignKey(
        Ecole, on_delete=models.CASCADE, related_name="budgets_annuels"
    )
    annee = models.ForeignKey(
        Annee_Scolaire, on_delete=models.CASCADE, related_name="budgets"
    )
    date_fixation = models.DateTimeField()
    date_maj = models.DateTimeField(auto_now=True)
    fixe_par = models.CharField(max_length=80, blank=True)
    commentaire = models.TextField(blank=True)
    capacite_totale = models.PositiveIntegerField(default=0)
    # Totaux minerval (détail par classe)
    total_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_cdf = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    # Totaux toutes rubriques
    total_recettes_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_recettes_cdf = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_depenses_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_depenses_cdf = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        ordering = ["-annee__anne_scolaire", "-date_fixation"]
        verbose_name = "Budget annuel"
        verbose_name_plural = "Budgets annuels"
        constraints = [
            models.UniqueConstraint(
                fields=["ecole", "annee"],
                name="uniq_budget_ecole_annee",
            )
        ]

    def __str__(self):
        return f"Budget {self.annee} — {self.ecole}"


class RubriqueBudget(models.Model):
    """Catalogue des rubriques d'un budget scolaire (recettes / dépenses)."""

    NATURE_CHOICES = [
        ("RECETTE", "Recette"),
        ("DEPENSE", "Dépense"),
    ]
    CALCUL_CHOICES = [
        ("", "Saisie manuelle"),
        ("MINERVAL", "Auto — capacité × minerval"),
        ("INSCRIPTION", "Auto — capacité × frais d'inscription"),
        ("SALAIRES", "Auto — salaires annuels (contrats × 12)"),
    ]

    code = models.CharField(max_length=40, unique=True)
    libelle = models.CharField(max_length=255)
    nature = models.CharField(max_length=10, choices=NATURE_CHOICES)
    ordre = models.PositiveIntegerField(default=100)
    calcul_auto = models.CharField(
        max_length=20, choices=CALCUL_CHOICES, blank=True, default=""
    )
    description = models.CharField(max_length=500, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nature", "ordre", "libelle"]
        verbose_name = "Rubrique de budget"
        verbose_name_plural = "Rubriques de budget"

    def __str__(self):
        return f"{self.code} — {self.libelle}"


class PosteBudget(models.Model):
    """Montant budgété pour une rubrique (snapshot annuel)."""

    budget = models.ForeignKey(
        BudgetAnnuel, on_delete=models.CASCADE, related_name="postes"
    )
    rubrique = models.ForeignKey(
        RubriqueBudget, on_delete=models.PROTECT, related_name="postes"
    )
    montant_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    montant_cdf = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    est_auto = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["rubrique__nature", "rubrique__ordre", "rubrique__libelle"]
        verbose_name = "Poste budgétaire"
        verbose_name_plural = "Postes budgétaires"
        constraints = [
            models.UniqueConstraint(
                fields=["budget", "rubrique"],
                name="uniq_poste_budget_rubrique",
            )
        ]

    def __str__(self):
        return f"{self.rubrique} — {self.montant_usd} USD / {self.montant_cdf} CDF"


class LigneBudget(models.Model):
    """Ligne de détail minerval : une classe × capacité × minerval unitaire."""

    budget = models.ForeignKey(
        BudgetAnnuel, on_delete=models.CASCADE, related_name="lignes"
    )
    classe = models.ForeignKey(
        Classe, on_delete=models.CASCADE, related_name="lignes_budget"
    )
    capacite = models.PositiveIntegerField(default=0)
    montant_unitaire = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    devise = models.ForeignKey(
        Devise, on_delete=models.PROTECT, null=True, blank=True
    )
    sous_total = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    type_frais_libelle = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["classe__section__section", "classe__classe"]
        verbose_name = "Ligne de budget minerval"
        verbose_name_plural = "Lignes de budget minerval"
        constraints = [
            models.UniqueConstraint(
                fields=["budget", "classe"],
                name="uniq_ligne_budget_classe",
            )
        ]

    def __str__(self):
        return f"{self.classe} — {self.sous_total}"


class ConfigWhatsApp(models.Model):
    """Configuration WhatsApp centrale (une instance pour toute la plateforme)."""

    PROVIDER_CHOICES = [
        ("BIRD", "Bird (WhatsApp)"),
        ("ULTRAMSG", "Ultramsg"),
        ("META", "Meta Cloud API (WhatsApp Business)"),
        ("LOG", "Mode test (journal uniquement)"),
    ]

    MESSAGE_DEFAUT = (
        "Bonjour {parent},\n\n"
        "Paiement reçu pour {eleve} ({classe}) à {ecole}.\n"
        "Reçu : {numero_recu}\n"
        "Frais : {frais}\n"
        "Montant : {montant} {devise}\n"
        "Mode : {mode}\n"
        "Date : {date}\n\n"
        "Merci."
    )

    ecole = models.OneToOneField(
        Ecole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="config_whatsapp",
        help_text="Laisser vide : configuration centrale partagée par toutes les écoles.",
    )
    actif = models.BooleanField(default=False)
    provider = models.CharField(
        max_length=20, choices=PROVIDER_CHOICES, default="BIRD"
    )
    api_token = models.TextField(
        blank=True,
        help_text="Token Ultramsg / Access token Meta (inutile avec Bird : la clé est dans .env)",
    )
    instance_id = models.CharField(
        max_length=80,
        blank=True,
        help_text="Instance ID Ultramsg ou Phone Number ID Meta (inutile avec Bird)",
    )
    api_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="URL API optionnelle (sinon URL par défaut du fournisseur)",
    )
    indicatif_pays = models.CharField(
        max_length=5,
        default="243",
        help_text="Indicatif sans + (ex. 243 pour la RDC)",
    )
    template_meta = models.CharField(
        max_length=100,
        blank=True,
        help_text="Modèle Meta reçu de paiement (ex. recu_paiement) ou slug Bird",
    )
    template_relance = models.CharField(
        max_length=100,
        blank=True,
        default="relance_minerval",
        help_text="Modèle Meta relance minerval (ex. relance_minerval)",
    )
    template_annonce = models.CharField(
        max_length=100,
        blank=True,
        default="annonce_ecole",
        help_text="Modèle Meta communication école → parents (ex. annonce_ecole)",
    )
    template_otp = models.CharField(
        max_length=100,
        blank=True,
        default="code_verification",
        help_text="Modèle Meta code OTP (ex. code_verification)",
    )
    template_langue = models.CharField(
        max_length=10,
        default="fr_FR",
        blank=True,
        help_text="Code langue Meta exact (souvent fr_FR, pas fr)",
    )
    # Ordre des variables {{1}}, {{2}}, … du corps du template Meta
    TEMPLATE_VARS_DEFAUT = "eleve,montant_affiche,numero_recu,frais,classe,date"
    template_variables = models.CharField(
        max_length=255,
        blank=True,
        default=TEMPLATE_VARS_DEFAUT,
        help_text=(
            "Clés séparées par des virgules, dans l'ordre des {{1}}, {{2}}, … "
            "Ex. eleve,montant_affiche,numero_recu,frais,classe,date"
        ),
    )
    message_modele = models.TextField(
        blank=True,
        help_text=(
            "Placeholders (Ultramsg / mode texte) : {parent} {eleve} {classe} "
            "{ecole} {numero_recu} {frais} {montant} {devise} {montant_affiche} "
            "{mode} {date}"
        ),
    )

    class Meta:
        verbose_name = "Configuration WhatsApp"
        verbose_name_plural = "Configurations WhatsApp"

    def __str__(self):
        etat = "actif" if self.actif else "inactif"
        if self.ecole_id:
            return f"WhatsApp {self.ecole} ({etat})"
        return f"WhatsApp central ({etat})"

    @classmethod
    def charger_pour_ecole(cls, ecole):
        """Config de l'école si elle existe et est active, sinon la config centrale."""
        if ecole is not None:
            locale = cls.objects.filter(ecole=ecole).order_by("pk").first()
            if locale and locale.actif:
                return locale
        return cls.charger_centrale()

    @classmethod
    def charger_centrale(cls):
        """Retourne (et crée si besoin) la configuration unique de la plateforme."""
        obj = cls.objects.filter(ecole__isnull=True).order_by("pk").first()
        if obj:
            return obj
        return cls.objects.create(
            ecole=None,
            provider="META",
            template_meta="recu_paiement",
            template_relance="relance_minerval",
            template_annonce="annonce_ecole",
            template_otp="code_verification",
            template_langue="fr",
            message_modele=cls.MESSAGE_DEFAUT,
            template_variables=cls.TEMPLATE_VARS_DEFAUT,
        )

    def modele_effectif(self):
        return (self.message_modele or "").strip() or self.MESSAGE_DEFAUT


class NotificationWhatsApp(models.Model):
    """Journal des notifications WhatsApp envoyées pour les paiements."""

    STATUT_CHOICES = [
        ("ENVOYE", "Envoyé"),
        ("ECHEC", "Échec"),
        ("IGNORE", "Ignoré"),
    ]

    ecole = models.ForeignKey(
        Ecole,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notif_whatsapp",
    )
    paiement = models.ForeignKey(
        Paiement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_whatsapp",
    )
    destinataire = models.CharField(max_length=20)
    message = models.TextField()
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default="ENVOYE")
    provider = models.CharField(max_length=20, blank=True)
    reponse_api = models.TextField(blank=True)
    erreur = models.TextField(blank=True)
    date_envoi = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_envoi"]
        verbose_name = "Notification WhatsApp"
        verbose_name_plural = "Notifications WhatsApp"

    def __str__(self):
        return f"WA {self.destinataire} — {self.statut} ({self.date_envoi})"


# -------------------------
# HOADA - Comptabilité
# -------------------------

class CompteComptable(models.Model):
    # Ex: 1000, 1101, 401, 512 ...
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, null=True, blank=True)
    numero = models.CharField(max_length=50)
    libelle = models.CharField(max_length=255)
    devise = models.ForeignKey(Devise, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("ecole", "numero")
        ordering = ["numero"]

    def __str__(self):
        return f"{self.numero} - {self.libelle}"


class JournalComptable(models.Model):
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, null=True, blank=True)
    code = models.CharField(max_length=30)
    libelle = models.CharField(max_length=255)

    class Meta:
        unique_together = ("ecole", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class PieceComptable(models.Model):
    # Référence/numéro pièce (ex: PV-0001, FACT-2024-001, etc.)
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, null=True, blank=True)
    reference = models.CharField(max_length=60)
    date = models.DateField()
    journal = models.ForeignKey(JournalComptable, on_delete=models.PROTECT)
    libelle = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("ecole", "reference")
        ordering = ["-date", "reference"]

    def __str__(self):
        return self.reference


class Ecriture(models.Model):
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, null=True, blank=True)
    date_ecriture = models.DateField()
    journal = models.ForeignKey(JournalComptable, on_delete=models.PROTECT)
    # On relie à une pièce; optionnel pour permettre des écritures sans pièce
    piece = models.ForeignKey(PieceComptable, on_delete=models.SET_NULL, null=True, blank=True)
    libelle = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-date_ecriture", "id"]

    def __str__(self):
        return f"Ecriture {self.id} ({self.journal.code})"


class EcritureLigne(models.Model):
    SENS_CHOICES = [
        ("DEBIT", "Débit"),
        ("CREDIT", "Crédit"),
    ]

    ecriture = models.ForeignKey(Ecriture, on_delete=models.CASCADE, related_name="lignes")
    compte = models.ForeignKey(CompteComptable, on_delete=models.PROTECT)
    sens = models.CharField(max_length=6, choices=SENS_CHOICES)
    montant = models.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        verbose_name = "Ligne d'écriture"
        verbose_name_plural = "Lignes d'écritures"

    def __str__(self):
        return f"{self.ecriture_id} - {self.compte.numero} {self.sens} {self.montant}"


from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver


@receiver(pre_save, sender=Paiement)
def _paiement_mémoriser_ancien_statut(sender, instance, **kwargs):
    instance._ancien_statut_whatsapp = None
    if instance.pk:
        try:
            instance._ancien_statut_whatsapp = (
                Paiement.objects.filter(pk=instance.pk)
                .values_list("statut", flat=True)
                .first()
            )
        except Exception:
            instance._ancien_statut_whatsapp = None


@receiver(post_save, sender=Paiement)
def auto_post_payment_to_entries(sender, instance, created, **kwargs):
    # VALIDE → crée l'écriture si absente ; autre statut → retire l'écriture.
    # La resync forcée (montant / mode / reçu) se fait dans paiement_update.
    try:
        from finances.views import _hoada_auto_post_payment_to_entries
        _hoada_auto_post_payment_to_entries(instance)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error auto posting payment: {e}", exc_info=True)

    try:
        from finances.paiement_utils import sync_frais_inscription_depuis_paiement
        sync_frais_inscription_depuis_paiement(instance)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error syncing frais_inscription: {e}", exc_info=True)

    # WhatsApp : à chaque nouveau paiement VALIDÉ (création ou passage à VALIDE)
    try:
        ancien = getattr(instance, "_ancien_statut_whatsapp", None)
        devenir_valide = instance.statut == "VALIDE" and (
            created or ancien != "VALIDE"
        )
        if devenir_valide:
            from finances.whatsapp import notifier_paiement_whatsapp
            notifier_paiement_whatsapp(instance)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            f"Error sending WhatsApp notification: {e}", exc_info=True
        )


@receiver(post_delete, sender=Paiement)
def sync_frais_inscription_on_delete(sender, instance, **kwargs):
    try:
        from finances.views import _hoada_delete_payment_entries, _hoada_ecole_from_paiement
        ecole = _hoada_ecole_from_paiement(instance)
        _hoada_delete_payment_entries(ecole, getattr(instance, "numero_recu", None))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            f"Error deleting HOADA entries on payment delete: {e}", exc_info=True
        )

    try:
        from finances.paiement_utils import sync_frais_inscription_depuis_paiement
        sync_frais_inscription_depuis_paiement(instance)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error syncing frais_inscription on delete: {e}", exc_info=True)


class IntentionPaiementMobile(models.Model):
    """Demande de paiement Mobile Money initiée par le parent (ou la caisse)."""

    PROVIDER_CHOICES = [
        ("AIRTEL", "Airtel Money"),
        ("ORANGE", "Orange Money"),
        ("MPESA", "M-Pesa"),
        ("FLEXPAIE", "FlexPaie"),
        ("AUTRE", "Autre"),
    ]
    STATUT_CHOICES = [
        ("INITIEE", "Initiée"),
        ("EN_ATTENTE", "En attente opérateur"),
        ("PAYEE", "Payée"),
        ("ECHEC", "Échec"),
        ("EXPIREE", "Expirée"),
    ]

    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name="intentions_mobile")
    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.CASCADE,
        related_name="intentions_mobile",
    )
    frais = models.ForeignKey(
        Frais_Scolaire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intentions_mobile",
    )
    montant = models.DecimalField(max_digits=20, decimal_places=2)
    devise = models.ForeignKey(Devise, on_delete=models.PROTECT)
    telephone = models.CharField(max_length=20)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="AIRTEL")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="INITIEE")
    reference = models.CharField(max_length=40, unique=True)
    reference_operateur = models.CharField(max_length=80, blank=True)
    paiement = models.ForeignKey(
        Paiement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intentions_mobile",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Intention de paiement mobile"
        verbose_name_plural = "Intentions de paiement mobile"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} — {self.montant} ({self.statut})"

    def save(self, *args, **kwargs):
        if not self.reference:
            from django.utils.crypto import get_random_string

            self.reference = "MM-" + get_random_string(12).upper()
        super().save(*args, **kwargs)



