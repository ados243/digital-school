from django import forms
from common.form_mixins import FormControlMixin
from grh.models import Personnel
from .models import (
    AffectationEnseignement,
    DivisionAnnee,
    Matiere,
    PeriodeBulletin,
    TravailCote,
    CoursEnLigne,
    ChapitreCours,
    LeconEnLigne,
    CoursEnDirect,
    RessourcePartagee,
)
from inscription.tenant import classes_for_ecole, annees_for_ecole
from .validators import (
    cours_video_max_mb,
    ressource_fichier_max_mb,
    type_ressource_depuis_nom,
    validate_cours_video,
    validate_ressource_fichier,
    VIDEO_EXTENSIONS,
)


class _InputOnlyCheckboxSelect(forms.CheckboxSelectMultiple):
    option_template_name = "django/forms/widgets/input.html"


class CoursMultiClassesFormMixin:
    """Sélection de plusieurs classes + synchro de la classe principale (FK)."""

    def _configurer_classes(self, classes_qs=None):
        self.fields["classes"].required = True
        self.fields["classes"].widget.attrs["class"] = "form-check-input"
        if classes_qs is not None:
            self.fields["classes"].queryset = classes_qs.select_related("section")
        self.fields["classes"].label_from_instance = (
            lambda c: f"{c.classe} — {c.section}" if getattr(c, "section_id", None) else str(c.classe)
        )

    def clean(self):
        cleaned = super().clean()
        classes = list(cleaned.get("classes") or [])
        matiere = cleaned.get("matiere")
        if not classes:
            self.add_error("classes", "Sélectionnez au moins une classe.")
            return cleaned
        if matiere:
            mauvaises = [c for c in classes if c.section_id != matiere.section_id]
            if mauvaises:
                self.add_error(
                    "classes",
                    "Toutes les classes doivent appartenir à la même section que la matière.",
                )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        classes = list(self.cleaned_data.get("classes") or [])
        if classes:
            instance.classe = classes[0]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


def _configure_video_upload_field(field):
    """Impose la limite de taille et l’indique dans l’UI."""
    max_mb = cours_video_max_mb()
    field.help_text = (
        f'MP4 ou WebM uniquement — taille maximale : {max_mb} Mo par vidéo '
        f'(hébergement sécurisé, sans YouTube).'
    )
    attrs = field.widget.attrs
    attrs['accept'] = 'video/mp4,video/webm,video/ogg,.mp4,.webm,.ogg,.mov'
    attrs['data-max-mb'] = str(max_mb)
    attrs['data-video-limit'] = '1'
    attrs['class'] = (attrs.get('class', '') + ' js-video-upload').strip()


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
        self.ecole = ecole
        self.classe = classe
        super().__init__(*args, **kwargs)
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


class CoursEnLigneForm(CoursMultiClassesFormMixin, FormControlMixin, forms.ModelForm):
    class Meta:
        model = CoursEnLigne
        fields = [
            'annee_scolaire', 'classes', 'matiere', 'titre', 'sous_titre',
            'description', 'objectifs', 'competences', 'prerequis',
            'public_cible', 'niveau', 'duree_minutes', 'image_couverture',
        ]
        labels = {
            'annee_scolaire': 'Année scolaire',
            'classes': 'Classes',
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
            'classes': _InputOnlyCheckboxSelect,
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
        help_texts = {
            'classes': 'Cochez toutes les classes où vous donnez ce cours.',
        }

    def __init__(self, *args, ecole=None, classes_qs=None, matieres_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        from inscription.tenant import annees_for_ecole

        if ecole:
            self.fields['annee_scolaire'].queryset = annees_for_ecole(ecole)
        self._configurer_classes(classes_qs)
        if matieres_qs is not None:
            self.fields['matiere'].queryset = matieres_qs


class ChapitreCoursForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = ChapitreCours
        fields = ['titre', 'resume', 'contenu', 'video', 'image', 'ordre', 'publie']
        labels = {
            'titre': 'Titre du chapitre',
            'resume': 'Résumé',
            'contenu': 'Introduction',
            'video': 'Vidéo du chapitre',
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
            'video': forms.ClearableFileInput(attrs={
                'accept': 'video/mp4,video/webm,video/ogg,.mp4,.webm,.ogg,.mov',
            }),
            'ordre': forms.NumberInput(attrs={'min': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'video' in self.fields:
            _configure_video_upload_field(self.fields['video'])

    def clean_video(self):
        video = self.cleaned_data.get('video')
        if video:
            validate_cours_video(video)
        return video


class LeconEnLigneForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = LeconEnLigne
        fields = [
            'titre', 'resume', 'type_contenu', 'contenu',
            'video', 'image', 'fichier', 'duree_minutes', 'ordre', 'publie',
        ]
        labels = {
            'titre': 'Titre du sous-chapitre',
            'resume': 'Résumé',
            'type_contenu': 'Type',
            'contenu': 'Contenu pédagogique',
            'video': 'Vidéo',
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
            'video': forms.ClearableFileInput(attrs={
                'accept': 'video/mp4,video/webm,video/ogg,.mp4,.webm,.ogg,.mov',
            }),
            'duree_minutes': forms.NumberInput(attrs={'min': '1'}),
            'ordre': forms.NumberInput(attrs={'min': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'video' in self.fields:
            _configure_video_upload_field(self.fields['video'])

    def clean_video(self):
        video = self.cleaned_data.get('video')
        if video:
            validate_cours_video(video)
        return video


class CoursEnDirectForm(CoursMultiClassesFormMixin, FormControlMixin, forms.ModelForm):
    class Meta:
        model = CoursEnDirect
        fields = [
            'annee_scolaire', 'classes', 'matiere', 'titre',
            'description', 'date_heure_prevue', 'duree_minutes',
        ]
        labels = {
            'annee_scolaire': 'Année scolaire',
            'classes': 'Classes',
            'matiere': 'Matière',
            'titre': 'Titre de la séance',
            'description': 'Description',
            'date_heure_prevue': 'Date et heure',
            'duree_minutes': 'Durée (minutes)',
        }
        widgets = {
            'classes': _InputOnlyCheckboxSelect,
            'titre': forms.TextInput(attrs={'placeholder': 'Ex: Révision fractions — séance live'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Sujets abordés, matériel à préparer…',
            }),
            'date_heure_prevue': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'duree_minutes': forms.NumberInput(attrs={'min': '15', 'step': '15'}),
        }
        help_texts = {
            'classes': 'Cochez toutes les classes qui participent à cette visioconférence.',
        }

    def __init__(self, *args, ecole=None, classes_qs=None, matieres_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_heure_prevue'].input_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
        ]
        if ecole:
            self.fields['annee_scolaire'].queryset = annees_for_ecole(ecole).filter(
                est_encoure=True
            )
            annee = self.fields['annee_scolaire'].queryset.first()
            if annee and not (self.instance and self.instance.pk):
                self.fields['annee_scolaire'].initial = annee.pk
                self.fields['annee_scolaire'].empty_label = None
        self._configurer_classes(classes_qs)
        if matieres_qs is not None:
            self.fields['matiere'].queryset = matieres_qs


class RessourcePartageeForm(FormControlMixin, forms.ModelForm):
    piece = forms.FileField(
        label='Fichier',
        required=False,
        help_text='Vidéo (MP4/WebM), PDF, image, document Office ou ZIP.',
    )

    class Meta:
        model = RessourcePartagee
        fields = ['annee_scolaire', 'classes', 'matiere', 'titre', 'description', 'publie']
        labels = {
            'annee_scolaire': 'Année scolaire',
            'classes': 'Classes',
            'matiere': 'Matière',
            'titre': 'Titre',
            'description': 'Description',
            'publie': 'Visible par les élèves',
        }
        widgets = {
            'classes': _InputOnlyCheckboxSelect,
            'titre': forms.TextInput(attrs={'placeholder': 'Ex: Fiche d’exercices — fractions'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Précisez l’usage du fichier (révision, devoir, support de cours…)',
            }),
        }
        help_texts = {
            'classes': 'Cochez les classes qui pourront télécharger ou consulter ce fichier.',
            'matiere': 'Facultatif — aide les élèves à classer la ressource.',
        }

    def __init__(self, *args, ecole=None, classes_qs=None, matieres_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['matiere'].required = False
        self.fields['matiere'].empty_label = 'Toutes matières / non précisée'
        self.fields['classes'].required = True
        self.fields['classes'].widget.attrs['class'] = 'form-check-input'
        if classes_qs is not None:
            self.fields['classes'].queryset = classes_qs.select_related('section')
        self.fields['classes'].label_from_instance = (
            lambda c: f"{c.classe} — {c.section}" if getattr(c, 'section_id', None) else str(c.classe)
        )
        if ecole:
            self.fields['annee_scolaire'].queryset = annees_for_ecole(ecole)
            annee = annees_for_ecole(ecole).filter(est_encoure=True).first()
            if annee and not (self.instance and self.instance.pk):
                self.fields['annee_scolaire'].initial = annee.pk
                self.fields['annee_scolaire'].empty_label = None
        if matieres_qs is not None:
            self.fields['matiere'].queryset = matieres_qs

        max_mb = max(cours_video_max_mb(), ressource_fichier_max_mb())
        piece = self.fields['piece']
        piece.widget.attrs.update({
            'accept': (
                'video/mp4,video/webm,video/ogg,.mp4,.webm,.ogg,.mov,'
                'application/pdf,.pdf,.doc,.docx,.odt,.xls,.xlsx,.ppt,.pptx,'
                'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.gif,.webp,.zip'
            ),
            'data-max-mb': str(max_mb),
            'data-file-limit': '1',
        })
        piece.help_text = (
            f'Vidéo jusqu’à {cours_video_max_mb()} Mo ; PDF et autres fichiers jusqu’à '
            f'{ressource_fichier_max_mb()} Mo.'
        )
        if self.instance and self.instance.pk and self.instance.piece:
            piece.help_text += f' Fichier actuel : {self.instance.nom_fichier()}.'
        else:
            piece.required = True

    def clean_piece(self):
        piece = self.cleaned_data.get('piece')
        if piece:
            validate_ressource_fichier(piece)
        return piece

    def clean(self):
        cleaned = super().clean()
        classes = list(cleaned.get('classes') or [])
        matiere = cleaned.get('matiere')
        piece = cleaned.get('piece')
        if not classes:
            self.add_error('classes', 'Sélectionnez au moins une classe.')
        if matiere and classes:
            mauvaises = [c for c in classes if c.section_id != matiere.section_id]
            if mauvaises:
                self.add_error(
                    'classes',
                    'Toutes les classes doivent appartenir à la même section que la matière.',
                )
        if not (self.instance and self.instance.pk and self.instance.piece) and not piece:
            self.add_error('piece', 'Ajoutez un fichier à partager.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        piece = self.cleaned_data.get('piece')
        if piece:
            nom = getattr(piece, 'name', '') or ''
            if any(nom.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                instance.video = piece
                instance.fichier = None
                instance.type_fichier = RessourcePartagee.TYPE_VIDEO
            else:
                instance.fichier = piece
                instance.video = None
                instance.type_fichier = type_ressource_depuis_nom(nom)
        if commit:
            instance.save()
            self.save_m2m()
        return instance

