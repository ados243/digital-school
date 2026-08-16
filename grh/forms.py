from django import forms
from common.form_mixins import FormControlMixin
from .models import Personnel, Contrat, Conge, Presence, Paie


class PersonnelForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Personnel
        exclude = ['ecole', 'utilisateur', 'matricule']
        labels = {
            'nom': 'Nom',
            'Post_nom': 'Post-nom',
            'prenom': 'Prénom',
            'sexe': 'Sexe',
            'date_de_naissance': 'Date de naissance',
            'nationalite': 'Nationalité',
            'quartier': 'Quartier',
            'adresse': 'Adresse',
            'photo': 'Photo',
            'telephone': 'Téléphone',
            'fonction': 'Fonction',
        }
        widgets = {
            'date_de_naissance': forms.DateInput(attrs={'type': 'date'}),
            'fonction': forms.Select(),
            'adresse': forms.TextInput(attrs={'placeholder': 'Avenue, numéro…'}),
            'telephone': forms.TextInput(attrs={'placeholder': 'Ex: 2438…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Conserve les anciennes fonctions libres lors d'une modification.
        choices = list(Personnel.FONCTION_CHOICES)
        current = getattr(self.instance, 'fonction', None)
        if self.instance and self.instance.pk and current:
            if current not in {c[0] for c in choices}:
                choices.append((current, current))
        self.fields['fonction'].choices = choices


class ContratForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Contrat
        fields = '__all__'
        labels = {
            'personnel': 'Membre du personnel',
            'type_contrat': 'Type de contrat',
            'date_debut': 'Date de début',
            'date_fin': 'Date de fin',
            'salaire_base': 'Salaire de base',
            'devise': 'Devise',
            'statut': 'Statut du contrat',
        }
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            'salaire_base': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
        help_texts = {
            'personnel': 'Un seul contrat par personne dans l’établissement. Les agents déjà sous contrat n’apparaissent pas.',
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Personnel.objects.all()
        if ecole is not None:
            qs = qs.filter(ecole=ecole)

        deja_ids = set(Contrat.objects.values_list('personnel_id', flat=True))
        current_id = None
        if self.instance and self.instance.pk and self.instance.personnel_id:
            current_id = self.instance.personnel_id
            deja_ids.discard(current_id)

        qs = qs.exclude(pk__in=deja_ids)
        if current_id:
            # Garantir que le titulaire actuel reste sélectionnable / visible
            qs = Personnel.objects.filter(pk=current_id) | qs

        self.fields['personnel'].queryset = qs.distinct().order_by(
            'nom', 'Post_nom', 'prenom'
        )
        if current_id:
            self.fields['personnel'].disabled = True

    def clean_personnel(self):
        if self.instance and self.instance.pk and self.fields['personnel'].disabled:
            return self.instance.personnel
        personnel = self.cleaned_data.get('personnel')
        if not personnel:
            return personnel
        qs = Contrat.objects.filter(personnel=personnel)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Ce membre du personnel a déjà un contrat dans cet établissement."
            )
        return personnel

    def clean(self):
        cleaned = super().clean()
        if self.instance and self.instance.pk and self.fields['personnel'].disabled:
            cleaned['personnel'] = self.instance.personnel
        return cleaned


class CongeForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Conge
        fields = ['personnel', 'type_conge', 'date_debut', 'date_fin', 'motif']
        labels = {
            'personnel': 'Membre du personnel',
            'type_conge': 'Type de congé',
            'date_debut': 'Date de début',
            'date_fin': 'Date de fin',
            'motif': 'Motif',
        }
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            'motif': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Motif de la demande…'}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ecole is not None:
            self.fields['personnel'].queryset = (
                Personnel.objects.filter(ecole=ecole).order_by('nom', 'Post_nom', 'prenom')
            )


class PresenceForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Presence
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'heure_arrivee': forms.TimeInput(attrs={'type': 'time'}),
            'heure_depart': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ecole is not None and 'personnel' in self.fields:
            self.fields['personnel'].queryset = (
                Personnel.objects.filter(ecole=ecole).order_by('nom', 'Post_nom', 'prenom')
            )


class PaieForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Paie
        fields = ['personnel', 'mois', 'annee', 'salaire_base', 'primes', 'deductions', 'devise', 'mode_paiement', 'statut_paiement', 'date_paiement']
        widgets = {
            'date_paiement': forms.DateInput(attrs={'type': 'date'}),
            'salaire_base': forms.NumberInput(attrs={'step': '0.01'}),
            'primes': forms.NumberInput(attrs={'step': '0.01'}),
            'deductions': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ecole is not None:
            self.fields['personnel'].queryset = (
                Personnel.objects.filter(ecole=ecole).order_by('nom', 'Post_nom', 'prenom')
            )
