from django import forms
from common.form_mixins import FormControlMixin
from grh.models import Personnel
from .models import AffectationEnseignement, DivisionAnnee, Matiere, PeriodeBulletin, TravailCote, CoursEnLigne, ChapitreCours, LeconEnLigne
from inscription.tenant import classes_for_ecole, annees_for_ecole


class MatiereForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ['code', 'libelle', 'coefficient', 'maxima_periode', 'section', 'enserignant']
        labels = {
            'code': 'Code matière',
            'libelle': 'Libellé',
            'coefficient': 'Coefficient',
            'maxima_periode': 'Maxima TJ / période (bulletin)',
            'section': 'Section',
            'enserignant': 'Enseignant de référence',
        }
        help_texts = {
            'enserignant': (
                "Facultatif au primaire : le titulaire de classe assure les cours "
                "sauf affectation spécifique classe/matière."
            ),
        }
        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'Ex: MATH101'}),
            'libelle': forms.TextInput(attrs={'placeholder': 'Ex: Mathématiques'}),
            'coefficient': forms.NumberInput(attrs={'step': '0.5', 'placeholder': 'Ex: 4.00'}),
            'maxima_periode': forms.NumberInput(attrs={'step': '1', 'min': '1', 'placeholder': 'Ex: 10'}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enserignant'].required = False
        self.fields['enserignant'].empty_label = "— Aucun (titulaire au primaire) —"
        if ecole:
            self.fields['enserignant'].queryset = (
                Personnel.objects.filter(
                    ecole=ecole,
                    fonction__in=['Enseignant', 'Préfet', 'Directeur des études'],
                )
                .order_by('nom', 'prenom')
            )
            self.fields['enserignant'].label_from_instance = (
                lambda p: f"{p.prenom} {p.nom} ({p.matricule})"
            )


class TravailCoteForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = TravailCote
        fields = [
            'annee_scolaire',
            'classe',
            'matiere',
            'type_travail',
            'role_bulletin',
            'periode',
            'division',
            'titre',
            'date_travail',
            'bareme',
            'coefficient',
        ]
        labels = {
            'annee_scolaire': 'Année scolaire',
            'classe': 'Classe',
            'matiere': 'Matière',
            'type_travail': 'Type de travail',
            'role_bulletin': 'Rôle sur le bulletin',
            'periode': 'Période (travaux journaliers)',
            'division': 'Trimestre / semestre (examen)',
            'titre': 'Intitulé (optionnel)',
            'date_travail': 'Date',
            'bareme': 'Barème (sur)',
            'coefficient': 'Coefficient',
        }
        help_texts = {
            'role_bulletin': (
                "TJ → colonne de la période sur le bulletin. "
                "EXAMEN → colonne EXAM. du trimestre ou du semestre."
            ),
            'periode': "Requis pour les travaux journaliers (devoirs, interros, TP…).",
            'division': "Requis pour l'examen de fin de trimestre / semestre.",
        }
        widgets = {
            'titre': forms.TextInput(attrs={'placeholder': 'Ex: Interrogation chapitre 3'}),
            'date_travail': forms.DateInput(attrs={'type': 'date'}),
            'bareme': forms.NumberInput(attrs={'step': '0.5', 'min': '1'}),
            'coefficient': forms.NumberInput(attrs={'step': '0.5', 'min': '0.5'}),
        }

    def __init__(self, *args, ecole=None, classes_qs=None, matieres_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['periode'].required = False
        self.fields['division'].required = False
        if ecole:
            self.fields['classe'].queryset = (
                classes_qs if classes_qs is not None
                else classes_for_ecole(ecole).order_by('classe')
            )
            self.fields['matiere'].queryset = (
                matieres_qs if matieres_qs is not None
                else Matiere.objects.filter(ecole=ecole).order_by('libelle')
            )
            self.fields['annee_scolaire'].queryset = annees_for_ecole(ecole).order_by('-anne_scolaire')
            annee = None
            if self.instance and self.instance.pk and self.instance.annee_scolaire_id:
                annee = self.instance.annee_scolaire
            elif self.data.get('annee_scolaire'):
                annee = annees_for_ecole(ecole).filter(pk=self.data.get('annee_scolaire')).first()
            elif self.initial.get('annee_scolaire'):
                annee = self.initial.get('annee_scolaire')

            periodes = PeriodeBulletin.objects.none()
            divisions = DivisionAnnee.objects.none()
            if annee:
                cycle_ids = set()
                for c in self.fields['classe'].queryset.select_related('section'):
                    if c.section_id:
                        cycle_ids.add(c.section.cycle_id)
                periodes = (
                    PeriodeBulletin.objects.filter(annee_scolaire=annee, cycle_id__in=cycle_ids)
                    .select_related('division', 'cycle')
                    .order_by('cycle__cycle', 'numero')
                )
                divisions = (
                    DivisionAnnee.objects.filter(annee_scolaire=annee, cycle_id__in=cycle_ids)
                    .select_related('cycle')
                    .order_by('cycle__cycle', 'numero')
                )
            self.fields['periode'].queryset = periodes
            self.fields['division'].queryset = divisions

    def clean(self):
        cleaned_data = super().clean()
        classe = cleaned_data.get('classe')
        matiere = cleaned_data.get('matiere')
        bareme = cleaned_data.get('bareme')
        type_travail = cleaned_data.get('type_travail')
        role = cleaned_data.get('role_bulletin')
        periode = cleaned_data.get('periode')
        division = cleaned_data.get('division')

        if type_travail in TravailCote.TYPES_EXAMEN:
            role = 'EXAMEN'
            cleaned_data['role_bulletin'] = role
        elif not role:
            role = 'TJ'
            cleaned_data['role_bulletin'] = role

        if classe and matiere and classe.section_id != matiere.section_id:
            self.add_error(
                'matiere',
                "Cette matière n'appartient pas à la section de la classe sélectionnée.",
            )

        if bareme is not None and bareme <= 0:
            self.add_error('bareme', "Le barème doit être supérieur à zéro.")

        if role == 'TJ':
            if not periode:
                self.add_error(
                    'periode',
                    "Indiquez la période du bulletin pour les travaux journaliers.",
                )
            elif classe and periode.cycle_id != classe.section.cycle_id:
                self.add_error(
                    'periode',
                    "Cette période ne correspond pas au cycle de la classe.",
                )
            else:
                cleaned_data['division'] = periode.division if periode else None
        elif role == 'EXAMEN':
            cleaned_data['periode'] = None
            if not division:
                self.add_error(
                    'division',
                    "Indiquez le trimestre ou le semestre pour l'examen.",
                )
            elif classe and division.cycle_id != classe.section.cycle_id:
                self.add_error(
                    'division',
                    "Cette division ne correspond pas au cycle de la classe.",
                )

        return cleaned_data


class AffectationEnseignementForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = AffectationEnseignement
        fields = ['matiere', 'enseignant']
        labels = {
            'matiere': 'Matière / cours',
            'enseignant': 'Professeur du cours',
        }
        help_texts = {
            'enseignant': (
                "Remplace le titulaire (primaire) ou l'enseignant de référence "
                "pour cette classe uniquement."
            ),
        }

    def __init__(self, *args, ecole=None, classe=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole = ecole
        self.classe = classe
        if ecole and classe:
            self.fields['matiere'].queryset = (
                Matiere.objects.filter(ecole=ecole, section=classe.section)
                .order_by('libelle')
            )
            self.fields['enseignant'].queryset = (
                Personnel.objects.filter(
                    ecole=ecole,
                    fonction__in=['Enseignant', 'Préfet', 'Directeur des études'],
                )
                .order_by('nom', 'prenom')
            )
            self.fields['enseignant'].label_from_instance = (
                lambda p: f"{p.prenom} {p.nom} ({p.matricule})"
            )
        else:
            self.fields['matiere'].queryset = Matiere.objects.none()
            self.fields['enseignant'].queryset = Personnel.objects.none()

    def clean(self):
        cleaned = super().clean()
        matiere = cleaned.get('matiere')
        enseignant = cleaned.get('enseignant')
        if self.classe and matiere and matiere.section_id != self.classe.section_id:
            self.add_error('matiere', "Cette matière n'appartient pas à la section de la classe.")
        if self.ecole and enseignant and enseignant.ecole_id != self.ecole.id:
            self.add_error('enseignant', "Cet enseignant n'appartient pas à votre école.")
        return cleaned


class CoursEnLigneForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = CoursEnLigne
        fields = [
            'annee_scolaire', 'classe', 'matiere', 'titre', 'sous_titre',
            'description', 'objectifs', 'competences', 'prerequis',
            'public_cible', 'niveau', 'duree_minutes', 'image_couverture',
        ]
        labels = {
            'annee_scolaire': 'Année scolaire',
            'classe': 'Classe',
            'matiere': 'Matière',
            'titre': 'Titre du cours',
            'sous_titre': 'Sous-titre',
            'description': 'À propos du cours',
            'objectifs': 'Ce que vous allez apprendre',
            'competences': 'Compétences',
            'prerequis': 'Prérequis',
            'public_cible': 'Public cible',
            'niveau': 'Niveau',
            'duree_minutes': 'Durée estimée (minutes)',
            'image_couverture': 'Image de couverture',
        }
        widgets = {
            'titre': forms.TextInput(attrs={'placeholder': 'Ex: Maîtriser les fractions'}),
            'sous_titre': forms.TextInput(attrs={
                'placeholder': 'Ex: Comprendre, calculer et appliquer les fractions au quotidien',
            }),
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Présentez le cours en détail : contexte, méthode, bénéfices…',
            }),
            'objectifs': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Un objectif par ligne\nEx: Identifier une fraction\nComparer deux fractions',
            }),
            'competences': forms.TextInput(attrs={
                'placeholder': 'Fractions, Calcul mental, Résolution de problèmes',
            }),
            'prerequis': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ex: Connaître les tables de multiplication',
            }),
            'public_cible': forms.TextInput(attrs={'placeholder': 'Ex: Élèves de 5e primaire'}),
            'duree_minutes': forms.NumberInput(attrs={'min': '0', 'placeholder': '0 = auto'}),
        }

    def __init__(self, *args, ecole=None, classes_qs=None, matieres_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        from inscription.tenant import annees_for_ecole

        if ecole:
            self.fields['annee_scolaire'].queryset = annees_for_ecole(ecole)
        if classes_qs is not None:
            self.fields['classe'].queryset = classes_qs
        if matieres_qs is not None:
            self.fields['matiere'].queryset = matieres_qs

    def clean(self):
        cleaned = super().clean()
        classe = cleaned.get('classe')
        matiere = cleaned.get('matiere')
        if classe and matiere and matiere.section_id != classe.section_id:
            self.add_error('matiere', "Cette matière n'appartient pas à la section de la classe.")
        return cleaned


class ChapitreCoursForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = ChapitreCours
        fields = ['titre', 'resume', 'contenu', 'video_url', 'image', 'ordre', 'publie']
        labels = {
            'titre': 'Titre du chapitre',
            'resume': 'Résumé',
            'contenu': 'Introduction',
            'video_url': 'Vidéo du chapitre',
            'image': 'Image du chapitre',
            'ordre': 'Ordre',
            'publie': 'Chapitre visible',
        }
        widgets = {
            'titre': forms.TextInput(attrs={'placeholder': 'Ex: Chapitre 1 — Les fractions'}),
            'resume': forms.TextInput(attrs={'placeholder': 'Ce que couvre ce chapitre…'}),
            'contenu': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Introduction affichée au début du chapitre…',
            }),
            'video_url': forms.URLInput(attrs={'placeholder': 'https://www.youtube.com/watch?v=…'}),
            'ordre': forms.NumberInput(attrs={'min': '1'}),
        }


class LeconEnLigneForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = LeconEnLigne
        fields = [
            'titre', 'resume', 'type_contenu', 'contenu',
            'video_url', 'image', 'fichier', 'duree_minutes', 'ordre', 'publie',
        ]
        labels = {
            'titre': 'Titre du sous-chapitre',
            'resume': 'Résumé',
            'type_contenu': 'Type',
            'contenu': 'Contenu pédagogique',
            'video_url': 'Lien vidéo',
            'image': 'Image',
            'fichier': 'Fichier joint',
            'duree_minutes': 'Durée (min)',
            'ordre': 'Ordre',
            'publie': 'Visible pour les élèves',
        }
        widgets = {
            'titre': forms.TextInput(attrs={'placeholder': 'Ex: 1.1 Définition d’une fraction'}),
            'resume': forms.TextInput(attrs={
                'placeholder': 'Ce que l’élève découvre dans ce sous-chapitre…',
            }),
            'contenu': forms.Textarea(attrs={
                'rows': 12,
                'placeholder': 'Rédigez le cours, les exemples, exercices et corrigés…',
            }),
            'video_url': forms.URLInput(attrs={'placeholder': 'https://www.youtube.com/watch?v=…'}),
            'duree_minutes': forms.NumberInput(attrs={'min': '1'}),
            'ordre': forms.NumberInput(attrs={'min': '1'}),
        }
