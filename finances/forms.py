import re
from django import forms
from decimal import Decimal
from common.form_mixins import FormControlMixin

from .models import (
    TypeFrais,
    Frais_Scolaire,
    Paiement,
    Devise,
    TauxChange,
    DemandeModificationPaiement,
    ConfigWhatsApp,
    CompteComptable,
    JournalComptable,
    PieceComptable,
    Ecriture,
    EcritureLigne,
)
from inscription.models import Inscription
from inscription.tenant import inscriptions_for_ecole, annees_for_ecole, sections_for_ecole
from .tenant import frais_for_ecole
from .paiement_utils import (
    frais_disponibles_pour_inscription,
    paiements_valides_par_frais,
    solde_frais,
    convertir_montant,
    _decimal,
)


def _inscription_label(ins):
    return f"{ins.eleve.prenom} {ins.eleve.nom} — {ins.classe} ({ins.annee_s})"


class TypeFraisForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = TypeFrais
        fields = ["libelle", "description"]
        labels = {
            "libelle": "Libellé du type de frais",
            "description": "Description",
        }
        widgets = {
            "libelle": forms.TextInput(attrs={"placeholder": "Ex: Frais d'inscription"}),
            "description": forms.TextInput(attrs={"placeholder": "Description optionnelle"}),
        }


class FraisScolaireForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Frais_Scolaire
        fields = ["type_frais", "annee", "section", "montant", "devise", "echeance", "est_obligatoire"]
        labels = {
            "type_frais": "Type de frais",
            "annee": "Année scolaire",
            "section": "Section concernée",
            "montant": "Montant",
            "devise": "Devise",
            "echeance": "Date d'échéance",
            "est_obligatoire": "Frais obligatoire",
        }
        widgets = {
            "echeance": forms.DateInput(attrs={"type": "date"}),
            "montant": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ecole:
            self.fields['type_frais'].queryset = TypeFrais.objects.filter(ecole=ecole)
            self.fields['annee'].queryset = annees_for_ecole(ecole)
            self.fields['section'].queryset = sections_for_ecole(ecole)


class TauxChangeForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = TauxChange
        fields = ["taux", "date_effet", "commentaire"]
        labels = {
            "taux": "Taux (CDF pour 1 USD)",
            "date_effet": "Date d'effet",
            "commentaire": "Commentaire",
        }
        widgets = {
            "taux": forms.NumberInput(
                attrs={"step": "0.0001", "min": "0.0001", "placeholder": "Ex: 2850"}
            ),
            "date_effet": forms.DateInput(attrs={"type": "date"}),
            "commentaire": forms.TextInput(
                attrs={"placeholder": "Optionnel — ex. cours du jour"}
            ),
        }

    def clean_taux(self):
        taux = self.cleaned_data.get("taux")
        if taux is None or taux <= 0:
            raise forms.ValidationError("Le taux doit être supérieur à zéro.")
        return taux


class ConfigWhatsAppForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = ConfigWhatsApp
        fields = [
            "actif",
            "provider",
            "api_token",
            "instance_id",
            "api_url",
            "indicatif_pays",
            "template_meta",
            "template_langue",
            "template_variables",
            "message_modele",
        ]
        labels = {
            "actif": "Activer les notifications WhatsApp",
            "provider": "Fournisseur",
            "api_token": "Token / Access token",
            "instance_id": "Instance ID (Ultramsg) ou Phone Number ID (Meta)",
            "api_url": "URL API (optionnel)",
            "indicatif_pays": "Indicatif pays (sans +)",
            "template_meta": "Nom du modèle Meta",
            "template_langue": "Langue du modèle Meta",
            "template_variables": "Variables du modèle (ordre {{1}}, {{2}}, …)",
            "message_modele": "Texte du message (Ultramsg / sans modèle Meta)",
        }
        widgets = {
            "api_token": forms.PasswordInput(
                render_value=True,
                attrs={"placeholder": "Token API", "autocomplete": "off"},
            ),
            "instance_id": forms.TextInput(attrs={"placeholder": "ex. instance12345"}),
            "api_url": forms.TextInput(
                attrs={"placeholder": "Laisser vide pour l'URL par défaut"}
            ),
            "indicatif_pays": forms.TextInput(attrs={"placeholder": "243"}),
            "template_meta": forms.TextInput(
                attrs={"placeholder": "ex. recu_paiement_ecole"}
            ),
            "template_langue": forms.TextInput(attrs={"placeholder": "fr"}),
            "template_variables": forms.TextInput(
                attrs={
                    "placeholder": ConfigWhatsApp.TEMPLATE_VARS_DEFAUT,
                }
            ),
            "message_modele": forms.Textarea(
                attrs={
                    "rows": 8,
                    "placeholder": ConfigWhatsApp.MESSAGE_DEFAUT,
                }
            ),
        }

    def clean_indicatif_pays(self):
        ind = re.sub(r"\D", "", self.cleaned_data.get("indicatif_pays") or "")
        if not ind:
            raise forms.ValidationError("Indicatif requis (ex. 243).")
        return ind

    def clean_template_langue(self):
        lang = (self.cleaned_data.get("template_langue") or "fr").strip()
        return lang or "fr"

    def clean_template_variables(self):
        from .whatsapp import CLES_CONTEXTE

        brut = (self.cleaned_data.get("template_variables") or "").strip()
        if not brut:
            return ConfigWhatsApp.TEMPLATE_VARS_DEFAUT
        cles = []
        inconnues = []
        for part in brut.split(","):
            cle = part.strip().lower().replace("{", "").replace("}", "")
            if not cle:
                continue
            if cle not in CLES_CONTEXTE:
                inconnues.append(cle)
            else:
                cles.append(cle)
        if inconnues:
            raise forms.ValidationError(
                "Clés inconnues : "
                + ", ".join(inconnues)
                + ". Autorisées : "
                + ", ".join(CLES_CONTEXTE)
            )
        if not cles:
            raise forms.ValidationError("Indiquez au moins une variable.")
        return ",".join(cles)


class DemandeModificationPaiementForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = DemandeModificationPaiement
        fields = ["motif"]
        labels = {"motif": "Motif de la correction"}
        widgets = {
            "motif": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Décrivez l'erreur de saisie (montant, élève, frais, devise…)",
                }
            ),
        }

    def clean_motif(self):
        motif = (self.cleaned_data.get("motif") or "").strip()
        if len(motif) < 10:
            raise forms.ValidationError(
                "Précisez le motif (au moins 10 caractères) pour aider l'administrateur."
            )
        return motif


class PaiementForm(FormControlMixin, forms.ModelForm):
    payer_en_francs = forms.BooleanField(
        required=False,
        label="Payer en francs (CDF)",
        help_text="Cochez si l'encaissement est reçu en CDF alors que le frais est en USD (ou l'inverse).",
    )
    montant_en_francs = forms.DecimalField(
        required=False,
        min_value=Decimal("0.01"),
        max_digits=20,
        decimal_places=2,
        label="Montant reçu en CDF",
        widget=forms.NumberInput(
            attrs={"step": "0.01", "min": "0", "placeholder": "0.00", "id": "id_montant_en_francs"}
        ),
    )
    taux_saisi = forms.DecimalField(
        required=False,
        min_value=Decimal("0.0001"),
        max_digits=18,
        decimal_places=4,
        label="Taux de change (CDF / 1 USD)",
        widget=forms.NumberInput(
            attrs={
                "step": "0.0001",
                "min": "0.0001",
                "placeholder": "Ex: 2850",
                "id": "id_taux_saisi",
            }
        ),
    )

    class Meta:
        model = Paiement
        fields = [
            "eleve",
            "frais",
            "montant_paye",
            "devise",
            "mode_paiement",
            "reference_trans",
            "caissier",
            "statut",
        ]
        labels = {
            "eleve": "Inscription / Élève",
            "frais": "Frais à encaisser",
            "montant_paye": "Montant encaissé",
            "devise": "Devise",
            "mode_paiement": "Mode de paiement",
            "reference_trans": "Référence transaction",
            "caissier": "Caissier",
            "statut": "Statut du paiement",
        }
        widgets = {
            "eleve": forms.Select(attrs={"id": "id_eleve"}),
            "frais": forms.Select(attrs={"id": "id_frais"}),
            "montant_paye": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "0.00", "id": "id_montant_paye"}),
            "devise": forms.Select(attrs={"id": "id_devise"}),
            "mode_paiement": forms.Select(attrs={"id": "id_mode_paiement"}),
            "reference_trans": forms.TextInput(attrs={"placeholder": "N° chèque, ID Mobile Money…", "id": "id_reference_trans"}),
            "caissier": forms.TextInput(attrs={"placeholder": "Nom du caissier"}),
        }

    def __init__(self, *args, ecole=None, exclude_paiement_id=None, taux_courant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole = ecole
        self.exclude_paiement_id = exclude_paiement_id
        self.taux_courant = taux_courant
        self._conversion_appliquee = False

        if ecole:
            self.fields["eleve"].queryset = (
                inscriptions_for_ecole(ecole)
                .select_related("eleve", "classe", "annee_s")
                .order_by("-date", "eleve__nom")
            )
            self.fields["eleve"].label_from_instance = _inscription_label
            self.fields["frais"].queryset = frais_for_ecole(ecole).select_related(
                "type_frais", "section", "annee", "devise"
            )

        self.fields["montant_paye"].required = False
        self.fields["reference_trans"].required = False

        if not self.is_bound:
            if self.instance.pk and self.instance.taux_change:
                self.fields["taux_saisi"].initial = self.instance.taux_change
                if self.instance.montant_origine is not None:
                    self.fields["montant_en_francs"].initial = self.instance.montant_origine
                    self.fields["payer_en_francs"].initial = True
            elif taux_courant is not None:
                self.fields["taux_saisi"].initial = taux_courant

        inscription = self._selected_inscription()
        if ecole and inscription:
            disponibles = frais_disponibles_pour_inscription(
                ecole, inscription, exclude_paiement_id=self.exclude_paiement_id
            )
            frais_ids = [item["frais"].pk for item in disponibles]
            if self.instance.pk and self.instance.frais_id:
                frais_ids.append(self.instance.frais_id)
            self.fields["frais"].queryset = frais_for_ecole(ecole).filter(
                pk__in=frais_ids
            ).select_related("type_frais", "section", "annee", "devise")

            def label_with_solde(frais):
                solde = solde_frais(
                    frais,
                    inscription.id,
                    paiements_valides_par_frais(ecole, self.exclude_paiement_id),
                )
                if solde["paye"] > 0:
                    return (
                        f"{frais.type_frais.libelle} — Reste : {solde['reste']} {frais.devise} "
                        f"(payé : {solde['paye']} / {solde['total']})"
                    )
                return f"{frais.type_frais.libelle} — {solde['total']} {frais.devise} (reste à payer)"

            self.fields["frais"].label_from_instance = label_with_solde

    def _selected_inscription(self):
        if self.data.get("eleve"):
            try:
                return self.fields["eleve"].queryset.get(pk=self.data["eleve"])
            except (Inscription.DoesNotExist, ValueError, TypeError):
                return None
        if self.instance.pk and self.instance.eleve_id:
            return self.instance.eleve
        initial = self.initial.get("eleve")
        return initial if isinstance(initial, Inscription) else None

    def clean(self):
        cleaned_data = super().clean()
        inscription = cleaned_data.get("eleve")
        frais = cleaned_data.get("frais")
        montant = cleaned_data.get("montant_paye")
        devise = cleaned_data.get("devise")
        mode = cleaned_data.get("mode_paiement")
        reference = cleaned_data.get("reference_trans")
        payer_en_francs = cleaned_data.get("payer_en_francs")
        montant_en_francs = cleaned_data.get("montant_en_francs")
        taux_saisi = cleaned_data.get("taux_saisi")

        if self.ecole and inscription and inscription.classe.ecole_id != self.ecole.id:
            raise forms.ValidationError("Cette inscription n'appartient pas à votre établissement.")

        devise_code = str(getattr(devise, "devise", "") or "").upper()
        frais_code = str(getattr(getattr(frais, "devise", None), "devise", "") or "").upper() if frais else ""

        # Paiement en CDF : montant_paye ou montant_en_francs = francs reçus
        paiement_en_cdf = bool(payer_en_francs) or devise_code == "CDF"
        if paiement_en_cdf and not montant_en_francs and montant is not None and montant > 0:
            # L'utilisateur a saisi les francs dans « Montant encaissé »
            montant_en_francs = montant
            cleaned_data["montant_en_francs"] = montant_en_francs
            cleaned_data["payer_en_francs"] = True
            payer_en_francs = True

        if paiement_en_cdf and frais and frais_code == "USD":
            if not montant_en_francs or montant_en_francs <= 0:
                # Si montant_paye était le champ utilisé pour les CDF
                if montant is not None and montant > 0 and devise_code == "CDF":
                    montant_en_francs = montant
                    cleaned_data["montant_en_francs"] = montant_en_francs
                else:
                    self.add_error(
                        "montant_en_francs" if payer_en_francs else "montant_paye",
                        "Indiquez le montant reçu en francs (CDF).",
                    )
            if not taux_saisi or taux_saisi <= 0:
                self.add_error(
                    "taux_saisi",
                    "Indiquez le taux de change (CDF pour 1 USD) pour convertir en dollars.",
                )
            if montant_en_francs and taux_saisi and taux_saisi > 0:
                try:
                    montant = convertir_montant(montant_en_francs, taux_saisi, "CDF", "USD")
                    cleaned_data["montant_paye"] = montant
                    usd = Devise.objects.filter(devise="USD").first()
                    if usd:
                        cleaned_data["devise"] = usd
                    self._conversion_appliquee = True
                    cleaned_data["_montant_origine"] = montant_en_francs
                    cleaned_data["_taux_change"] = taux_saisi
                    cleaned_data["_devise_origine"] = Devise.objects.filter(devise="CDF").first()
                except ValueError as exc:
                    self.add_error("taux_saisi", str(exc))
        elif payer_en_francs and frais and frais_code == "CDF":
            if not montant_en_francs or montant_en_francs <= 0:
                self.add_error("montant_en_francs", "Indiquez le montant reçu en francs.")
            else:
                montant = _decimal(montant_en_francs)
                cleaned_data["montant_paye"] = montant
                cleaned_data["devise"] = frais.devise
                self._conversion_appliquee = True
                cleaned_data["_montant_origine"] = montant_en_francs
                cleaned_data["_taux_change"] = taux_saisi
                cleaned_data["_devise_origine"] = frais.devise

        if inscription and frais:
            if frais.section_id != inscription.classe.section_id or frais.annee_id != inscription.annee_s_id:
                raise forms.ValidationError(
                    "Le frais sélectionné ne correspond pas à la section ou à l'année scolaire de l'élève."
                )
            solde = solde_frais(
                frais,
                inscription.id,
                paiements_valides_par_frais(self.ecole, self.exclude_paiement_id),
            )
            if solde["est_solde"]:
                raise forms.ValidationError("Ce frais est déjà entièrement payé pour cet élève.")
            # Comparer toujours dans la devise du frais (après conversion éventuelle)
            montant_a_comparer = cleaned_data.get("montant_paye")
            if montant_a_comparer is not None and montant_a_comparer > solde["reste"]:
                self.add_error(
                    "montant_paye",
                    f"Le montant converti ({montant_a_comparer} {frais.devise}) "
                    f"ne peut pas dépasser le reste à payer ({solde['reste']} {frais.devise}).",
                )

        montant = cleaned_data.get("montant_paye")
        if montant is not None and montant <= 0:
            self.add_error("montant_paye", "Le montant encaissé doit être supérieur à zéro.")
        elif montant is None and not paiement_en_cdf:
            self.add_error("montant_paye", "Indiquez le montant encaissé.")

        if mode and mode != "ESPECES" and not reference:
            self.add_error(
                "reference_trans",
                "Indiquez une référence pour les paiements par chèque, virement ou mobile money.",
            )

        return cleaned_data

    def save(self, commit=True):
        paiement = super().save(commit=False)
        if self._conversion_appliquee:
            paiement.taux_change = self.cleaned_data.get("_taux_change")
            paiement.montant_origine = self.cleaned_data.get("_montant_origine")
            paiement.devise_origine = self.cleaned_data.get("_devise_origine")
        elif not self.cleaned_data.get("payer_en_francs"):
            devise = self.cleaned_data.get("devise")
            if not (devise and str(devise.devise).upper() == "CDF"):
                paiement.taux_change = None
                paiement.montant_origine = None
                paiement.devise_origine = None
        if commit:
            paiement.save()
        return paiement


class CompteComptableForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = CompteComptable
        fields = ["numero", "libelle", "devise"]
        labels = {
            "numero": "Numéro de compte",
            "libelle": "Libellé",
            "devise": "Devise",
        }


class JournalComptableForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = JournalComptable
        fields = ["code", "libelle"]
        labels = {"code": "Code journal", "libelle": "Libellé"}


class EcritureForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Ecriture
        fields = ["date_ecriture", "journal", "piece", "libelle"]
        labels = {
            "date_ecriture": "Date d'écriture",
            "journal": "Journal",
            "piece": "Pièce comptable",
            "libelle": "Libellé",
        }
        widgets = {"date_ecriture": forms.DateInput(attrs={"type": "date"})}


class EcritureLigneForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = EcritureLigne
        fields = ["compte", "sens", "montant"]
        labels = {"compte": "Compte", "sens": "Sens", "montant": "Montant"}
        widgets = {"montant": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}
