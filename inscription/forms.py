from django import forms
from common.form_mixins import FormControlMixin
from .models import Tuteur, Eleve, Inscription, Classe, Annee_Scolaire, Quartier, Commune
from .tenant import eleves_for_ecole, tuteurs_for_ecole


class QuartierForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Quartier
        fields = ['commune', 'quartier']
        labels = {
            'commune': 'Commune',
            'quartier': 'Nom du quartier',
        }
        widgets = {
            'quartier': forms.TextInput(attrs={'placeholder': 'Ex. Lingwala, Gombe…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['commune'].queryset = Commune.objects.order_by('commune')
        self.fields['commune'].empty_label = '— Sélectionner une commune —'


class TuteurForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Tuteur
        exclude = ['ecole', 'matricule']
        labels = {
            'nom': 'Nom',
            'Post_nom': 'Post-nom',
            'prenom': 'Prénom',
            'lien_parente': 'Lien de parenté',
            'telephone': 'Téléphone principal',
            'telephone2': 'Téléphone secondaire',
            'email': 'E-mail',
            'quartier': 'Quartier de résidence',
            'adresse': 'Adresse de résidence',
        }
        widgets = {
            'adresse': forms.TextInput(attrs={'placeholder': 'Avenue, numéro, commune…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quartier'].required = True
        self.fields['adresse'].required = True
        self.fields['email'].required = False
        self.fields['telephone2'].required = False
        if 'quartier' in self.fields:
            self.fields['quartier'].queryset = (
                self.fields['quartier'].queryset.select_related('commune').order_by(
                    'commune__commune', 'quartier'
                )
            )
            self.fields['quartier'].label_from_instance = (
                lambda q: f"{q.quartier} ({q.commune.commune})"
            )


class EleveForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Eleve
        exclude = ['ecole', 'matricule']
        labels = {
            'nom': 'Nom',
            'Post_nom': 'Post-nom',
            'prenom': 'Prénom',
            'titeur': 'Tuteur / parent',
            'sexe': 'Sexe',
            'date_de_naissance': 'Date de naissance',
            'nationalite': 'Nationalité',
            'photo': 'Photo',
        }
        widgets = {
            'date_de_naissance': forms.DateInput(attrs={'type': 'date'}),
            'titeur': forms.Select(attrs={'id': 'id_titeur'}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole = ecole
        self.fields['titeur'].queryset = tuteurs_for_ecole(ecole).order_by(
            'nom', 'prenom'
        )
        self.fields['titeur'].label_from_instance = (
            lambda t: f"{t.prenom} {t.nom} {t.Post_nom} · {t.matricule}"
        )
        # Pas de sexe pré-sélectionné à la création
        self.fields['sexe'].choices = [('', '— Sélectionner —')] + list(Eleve.Sexe_choices)
        self.fields['sexe'].required = True
        if not self.instance.pk:
            self.fields['sexe'].initial = ''
            if not self.is_bound:
                self.initial['sexe'] = ''

    def clean_titeur(self):
        tuteur = self.cleaned_data.get('titeur')
        if tuteur and self.ecole and tuteur.ecole_id != self.ecole.id:
            raise forms.ValidationError(
                "Ce tuteur n'appartient pas à votre établissement."
            )
        return tuteur


class InscriptionForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Inscription
        fields = ['eleve', 'classe', 'annee_s', 'type_iscription', 'frais_inscription']
        labels = {
            'eleve': 'Élève',
            'classe': 'Classe d\'affectation',
            'annee_s': 'Année scolaire',
            'type_iscription': 'Type d\'inscription',
            'frais_inscription': 'Frais d\'inscription payés',
        }
        widgets = {
            'eleve': forms.Select(attrs={'id': 'id_eleve'}),
            'classe': forms.Select(attrs={'id': 'id_classe'}),
            'annee_s': forms.Select(attrs={'id': 'id_annee_s'}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole = ecole
        if ecole:
            self.fields['eleve'].queryset = eleves_for_ecole(ecole).order_by('nom', 'prenom')
            self.fields['eleve'].label_from_instance = (
                lambda e: f"{e.prenom} {e.nom} {e.Post_nom} · {e.matricule}".strip()
            )
            self.fields['eleve'].empty_label = "— Sélectionner un élève —"
            self.fields['classe'].queryset = (
                Classe.objects.filter(ecole=ecole).select_related('section').order_by('section__section', 'classe')
            )
            self.fields['classe'].label_from_instance = lambda c: f"{c.classe} — {c.section} (Salle {c.salle})"
            self.fields['annee_s'].queryset = Annee_Scolaire.objects.all().order_by('-est_encoure', '-date_debut')

    def clean(self):
        cleaned_data = super().clean()
        eleve = cleaned_data.get('eleve')
        classe = cleaned_data.get('classe')
        annee_s = cleaned_data.get('annee_s')

        if self.ecole and eleve and eleve.ecole_id != self.ecole.id:
            raise forms.ValidationError("Cet élève n'appartient pas à votre établissement.")

        if classe and annee_s and classe.capacite_max > 0:
            inscriptions = Inscription.objects.filter(classe=classe, annee_s=annee_s)
            if self.instance.pk:
                inscriptions = inscriptions.exclude(pk=self.instance.pk)
            if inscriptions.count() >= classe.capacite_max:
                raise forms.ValidationError(
                    f"La classe {classe} a atteint sa capacité maximale ({classe.capacite_max} élèves) "
                    f"pour l'année {annee_s}."
                )
        return cleaned_data


class ClasseForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Classe
        fields = ['section', 'classe', 'capacite_max', 'salle', 'titulaire']
        labels = {
            'section': 'Section pédagogique',
            'classe': 'Nom de la classe',
            'capacite_max': 'Capacité maximale',
            'salle': 'Salle',
            'titulaire': 'Enseignant titulaire',
        }
        widgets = {
            'classe': forms.TextInput(attrs={'placeholder': 'Ex: 6ème A'}),
            'capacite_max': forms.NumberInput(attrs={'min': '1'}),
            'salle': forms.TextInput(attrs={'placeholder': 'Ex: S12'}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole = ecole
        self.fields['titulaire'].required = False
        self.fields['titulaire'].empty_label = "— Aucun enseignant —"
        from grh.models import Personnel
        from django.db.models import Q

        if ecole:
            qs = Personnel.objects.filter(
                ecole=ecole,
            ).filter(
                Q(fonction__in=['Enseignant', 'Préfet', 'Directeur des études'])
                | Q(pk=getattr(self.instance, 'titulaire_id', None))
            ).order_by('nom', 'prenom')
            self.fields['titulaire'].queryset = qs
            self.fields['titulaire'].label_from_instance = (
                lambda p: f"{p.prenom} {p.nom} {p.Post_nom} · {p.fonction} · {p.matricule}".strip()
            )
        else:
            self.fields['titulaire'].queryset = Personnel.objects.none()

    def clean_titulaire(self):
        titulaire = self.cleaned_data.get('titulaire')
        if self.ecole and titulaire and titulaire.ecole_id != self.ecole.id:
            raise forms.ValidationError("Cet enseignant n'appartient pas à votre établissement.")
        return titulaire
