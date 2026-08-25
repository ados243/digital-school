import re
from django import forms
from django.db.models import Q
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
from inscription.tenant import inscriptions_for_ecole, annees_for_ecole, sections_for_ecole, classes_for_ecole
from .tenant import frais_for_ecole
from .paiement_utils import (
    frais_disponibles_pour_inscription,
    frais_concerne_inscription,
    paiements_valides_par_frais,
    solde_frais,
    convertir_montant,
    _decimal,
)


class _InputOnlyRadioSelect(forms.RadioSelect):
    option_template_name = "django/forms/widgets/input.html"


class _InputOnlyCheckboxSelect(forms.CheckboxSelectMultiple):
    option_template_name = "django/forms/widgets/input.html"


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
    PORTEE_SECTION = "section"
    PORTEE_CLASSES = "classes"
    PORTEE_CHOICES = [
        (PORTEE_SECTION, "Toute une section"),
        (PORTEE_CLASSES, "Une ou plusieurs classes"),
    ]
    portee = forms.ChoiceField(
        choices=PORTEE_CHOICES,
        widget=_InputOnlyRadioSelect,
        initial=PORTEE_SECTION,
        label="Portée du frais",
    )

    class Meta:
        model = Frais_Scolaire
        fields = ["type_frais", "annee", "section", "classes", "montant", "devise", "echeance", "est_obligatoire"]
        labels = {
            "type_frais": "Type de frais",
            "annee": "Année scolaire",
            "section": "Section concernée",
            "classes": "Classes concernées",
            "montant": "Montant",
            "devise": "Devise",
            "echeance": "Date d'échéance",
            "est_obligatoire": "Frais obligatoire",
        }
        widgets = {
            "echeance": forms.DateInput(attrs={"type": "date"}),
            "montant": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "classes": _InputOnlyCheckboxSelect,
        }
        help_texts = {
            "classes": "Cochez une ou plusieurs classes. Le frais ne sera dû que par leurs élèves.",
        }

    def __init__(self, *args, ecole=None, **kwargs):
        self.ecole = ecole
        super().__init__(*args, **kwargs)
        self.fields["section"].required = False
        self.fields["classes"].required = False
        self.fields["classes"].widget.attrs["class"] = "form-check-input"
        self.fields["classes"].queryset = classes_for_ecole(ecole).select_related("section").order_by(
            "section__section", "classe"
        )
        if ecole:
            self.fields["classes"].label_from_instance = (
                lambda c: f"{c.classe} — {c.section}"
            )
            self.fields["type_frais"].queryset = TypeFrais.objects.filter(ecole=ecole)
            annee_qs = annees_for_ecole(ecole).filter(est_encoure=True)
            if self.instance and self.instance.pk and self.instance.annee_id:
                annee_qs = annees_for_ecole(ecole).filter(
                    Q(est_encoure=True) | Q(pk=self.instance.annee_id)
                )
            self.fields["annee"].queryset = annee_qs
            self.fields["section"].queryset = sections_for_ecole(ecole)
            annee_courante = annee_qs.filter(est_encoure=True).first()
            if annee_courante and not (self.instance and self.instance.pk):
                self.fields["annee"].initial = annee_courante.pk
                self.fields["annee"].empty_label = None
        if self.instance and self.instance.pk and self.instance.est_specifique():
            self.fields["portee"].initial = self.PORTEE_CLASSES

    def clean(self):
        cleaned = super().clean()
        portee = cleaned.get("portee")
        section = cleaned.get("section")
        classes = cleaned.get("classes")
        if portee == self.PORTEE_SECTION:
            if not section:
                self.add_error("section", "Choisissez la section concernée.")
        elif portee == self.PORTEE_CLASSES:
            if not classes:
                    self.add_error("classes", "Sélectionnez au moins une classe.")
            elif self.ecole:
                etrangeres = [c for c in classes if c.ecole_id != self.ecole.id]
                if etrangeres:
                    self.add_error("classes", "Une classe n'appartient pas à votre établissement.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        portee = self.cleaned_data.get("portee")
        if portee == self.PORTEE_CLASSES:
            instance.section = None
        if commit:
            instance.save()
            if portee == self.PORTEE_CLASSES:
                instance.classes.set(self.cleaned_data.get("classes") or [])
            else:
                instance.classes.clear()
        return instance


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
            "template_relance",
            "template_annonce",
            "template_otp",
            "template_langue",
            "template_variables",
            "message_modele",
        ]
        labels = {
            "actif": "Activer les notifications WhatsApp",
            "provider": "Fournisseur",
            "api_token": "Token / Access token",
            "instance_id": "Phone Number ID (Meta) ou Instance ID (Ultramsg)",
            "api_url": "URL API (optionnel)",
            "indicatif_pays": "Indicatif pays (sans +)",
            "template_meta": "Template reçu de paiement",
            "template_relance": "Template relance minerval",
            "template_annonce": "Template annonce école → parents",
            "template_otp": "Template code OTP",
            "template_langue": "Langue des templates",
            "template_variables": "Variables du reçu Meta (ordre {{1}}, {{2}}, …)",
            "message_modele": "Texte du message (Ultramsg / sans modèle)",
        }
        help_texts = {
            "provider": (
                "Meta Cloud API : token et Phone Number ID ci-dessous. "
                "Bird : clé API dans .env (BIRD_API_KEY), secours OTP si Meta inactif."
            ),
            "api_token": (
                "Inutile avec Bird. Meta : jeton permanent (Utilisateur système). "
                "Laisser vide pour conserver le jeton déjà enregistré."
            ),
            "instance_id": (
                "Inutile avec Bird. Meta : Phone number ID (chiffres), pas le numéro +243…"
            ),
            "template_meta": "Meta : recu_de_paiement. Bird : bird_delivery_update.",
            "template_relance": "Meta : relance_minerval.",
            "template_annonce": "Meta : annonce_ecole.",
            "template_otp": (
                "Meta : nom exact du modèle Authentification (souvent "
                "code_verification). Catégorie Authentication, approuvé."
            ),
        }
        widgets = {
            "api_token": forms.PasswordInput(
                render_value=False,
                attrs={
                    "placeholder": "Laisser vide pour conserver le jeton actuel",
                    "autocomplete": "new-password",
                    "spellcheck": "false",
                },
            ),
            "instance_id": forms.TextInput(
                attrs={"placeholder": "ex. 123456789012345 (Phone Number ID Meta)"}
            ),
            "api_url": forms.TextInput(
                attrs={"placeholder": "Laisser vide pour l'URL par défaut"}
            ),
            "indicatif_pays": forms.TextInput(attrs={"placeholder": "243"}),
            "template_meta": forms.TextInput(
                attrs={"placeholder": "ex. recu_de_paiement"}
            ),
            "template_relance": forms.TextInput(
                attrs={"placeholder": "ex. relance_minerval"}
            ),
            "template_annonce": forms.TextInput(
                attrs={"placeholder": "ex. annonce_ecole"}
            ),
            "template_otp": forms.TextInput(
                attrs={"placeholder": "ex. code_verification"}
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

    def clean_api_token(self):
        token = (self.cleaned_data.get("api_token") or "").strip()
        if not token:
            if self.instance and getattr(self.instance, "pk", None):
                return self.instance.api_token
            return token
        # Évite un double « Bearer » si l'utilisateur colle l'en-tête complet
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        from common.secrets_crypto import chiffrer_secret

        return chiffrer_secret(token)

    def clean_api_url(self):
        from finances.whatsapp import valider_api_url_whatsapp

        url = (self.cleaned_data.get("api_url") or "").strip()
        if not url:
            return ""
        ok, err = valider_api_url_whatsapp(url, self.cleaned_data.get("provider") or "")
        if not ok:
            raise forms.ValidationError(err or "URL API non autorisée.")
        return url.rstrip("/")

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
        self.ecole = ecole
        self.exclude_paiement_id = exclude_paiement_id
        self.taux_courant = taux_courant
        self._conversion_appliquee = False
        super().__init__(*args, **kwargs)

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
            ).select_related("type_frais", "section", "annee", "devise").prefetch_related("classes")

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
            if not frais_concerne_inscription(frais, inscription):
                raise forms.ValidationError(
                    "Le frais sélectionné ne s'applique pas à la classe ou à l'année scolaire de l'élève."
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

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ecole is not None:
            self.ecole = ecole
        elif getattr(self.instance, "ecole_id", None):
            self.ecole = self.instance.ecole
        else:
            self.ecole = None
        if self.ecole is not None:
            self.fields["journal"].queryset = JournalComptable.objects.filter(
                ecole=self.ecole
            ).order_by("code")
            self.fields["piece"].queryset = PieceComptable.objects.filter(
                ecole=self.ecole
            ).order_by("-date", "reference")
        else:
            self.fields["journal"].queryset = JournalComptable.objects.none()
            self.fields["piece"].queryset = PieceComptable.objects.none()

    @staticmethod
    def _ecole_pk(ecole):
        return getattr(ecole, "pk", ecole)

    def clean_journal(self):
        journal = self.cleaned_data.get("journal")
        if journal and self.ecole and journal.ecole_id != self._ecole_pk(self.ecole):
            raise forms.ValidationError("Journal hors de votre école.")
        return journal

    def clean_piece(self):
        piece = self.cleaned_data.get("piece")
        if piece and self.ecole and piece.ecole_id != self._ecole_pk(self.ecole):
            raise forms.ValidationError("Pièce comptable hors de votre école.")
        return piece


class EcritureLigneForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = EcritureLigne
        fields = ["compte", "sens", "montant"]
        labels = {"compte": "Compte", "sens": "Sens", "montant": "Montant"}
        widgets = {"montant": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}
