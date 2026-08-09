from django.contrib import admin

from .models import (
    Devise,
    TypeFrais,
    Frais_Scolaire,
    Paiement,
    TauxChange,
    DemandeModificationPaiement,
    ConfigWhatsApp,
    NotificationWhatsApp,
    # HOADA
    CompteComptable,
    JournalComptable,
    PieceComptable,
    Ecriture,
    EcritureLigne,
)


@admin.register(Devise)
class DeviseAdmin(admin.ModelAdmin):
    list_display = ("devise",)
    search_fields = ("devise",)


@admin.register(TauxChange)
class TauxChangeAdmin(admin.ModelAdmin):
    list_display = ("ecole", "taux", "date_effet", "date_saisie", "saisi_par")
    list_filter = ("ecole", "date_effet")
    search_fields = ("commentaire", "saisi_par")


@admin.register(DemandeModificationPaiement)
class DemandeModificationPaiementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "paiement",
        "demande_par",
        "statut",
        "date_demande",
        "traite_par",
        "date_traitement",
    )
    list_filter = ("statut", "date_demande")
    search_fields = ("motif", "demande_par", "paiement__numero_recu")


@admin.register(TypeFrais)
class TypeFraisAdmin(admin.ModelAdmin):
    list_display = ("libelle", "ecole")
    search_fields = ("libelle", "description")


@admin.register(Frais_Scolaire)
class FraisScolaireAdmin(admin.ModelAdmin):
    list_display = ("type_frais", "annee", "section", "montant", "devise", "echeance", "est_obligatoire")
    list_filter = ("annee", "section", "devise", "est_obligatoire")
    search_fields = ("type_frais__libelle",)


@admin.register(ConfigWhatsApp)
class ConfigWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("ecole", "actif", "provider", "indicatif_pays")
    list_filter = ("actif", "provider")


@admin.register(NotificationWhatsApp)
class NotificationWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("date_envoi", "ecole", "destinataire", "paiement", "statut", "provider")
    list_filter = ("statut", "provider", "ecole")
    search_fields = ("destinataire", "message", "erreur", "paiement__numero_recu")
    readonly_fields = ("date_envoi",)


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = (
        "numero_recu",
        "eleve",
        "frais",
        "montant_paye",
        "devise",
        "taux_change",
        "montant_origine",
        "mode_paiement",
        "statut",
        "date_encodage",
    )
    list_filter = ("statut", "mode_paiement", "devise", "date_encodage")
    search_fields = ("numero_recu", "reference_trans")


# -------------------------
# HOADA - Comptabilité
# -------------------------

@admin.register(CompteComptable)
class CompteComptableAdmin(admin.ModelAdmin):
    list_display = ("numero", "libelle", "devise")
    search_fields = ("numero", "libelle")


@admin.register(JournalComptable)
class JournalComptableAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle")
    search_fields = ("code", "libelle")


@admin.register(PieceComptable)
class PieceComptableAdmin(admin.ModelAdmin):
    list_display = ("reference", "date", "journal", "libelle")
    search_fields = ("reference", "libelle")
    list_filter = ("journal", "date")


@admin.register(Ecriture)
class EcritureAdmin(admin.ModelAdmin):
    list_display = ("id", "date_ecriture", "journal", "piece", "libelle")
    search_fields = ("libelle", "piece__reference", "journal__code")
    list_filter = ("journal", "date_ecriture")


@admin.register(EcritureLigne)
class EcritureLigneAdmin(admin.ModelAdmin):
    list_display = ("id", "ecriture", "compte", "sens", "montant")
    search_fields = ("ecriture__id", "compte__numero", "compte__libelle")
    list_filter = ("sens", "compte", "ecriture__journal")

