from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

from common.form_mixins import FormControlMixin
from inscription.models import Ecole, Eleve, Tuteur
from .models import Utilisateur


def _normalise(texte):
    return (texte or "").strip().casefold()


class ConnexionForm(FormControlMixin, AuthenticationForm):
    username = forms.CharField(label="Identifiant", widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)


class InscriptionForm(FormControlMixin, forms.Form):
    """Auto-inscription : le compte est rattaché à une fiche déjà créée par
    l'école (élève, tuteur ou membre du personnel), identifiée par son
    matricule et vérifiée par le nom, pour éviter toute usurpation."""

    profil = forms.ChoiceField(
        choices=Utilisateur.PROFIL_CHOICES,
        widget=forms.RadioSelect,
        label="Je suis…",
    )
    ecole = forms.ModelChoiceField(
        queryset=Ecole.objects.filter(activation=True).order_by('ecole'),
        label="Établissement",
        empty_label="Sélectionnez votre établissement",
        required=False,
    )
    matricule = forms.CharField(
        label="Matricule",
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': "Matricule communiqué par l'école"}),
    )
    nom = forms.CharField(
        label="Nom",
        max_length=250,
        widget=forms.TextInput(attrs={'placeholder': 'Tel qu\'enregistré par l\'école'}),
    )
    prenom = forms.CharField(label="Prénom", max_length=255)
    email = forms.EmailField(label="Adresse e-mail", required=False)
    username = forms.CharField(label="Identifiant de connexion", max_length=150)
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if Utilisateur.objects.filter(username__iexact=username).exists():
            raise ValidationError("Cet identifiant est déjà utilisé. Choisissez-en un autre.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        profil = cleaned_data.get('profil')
        ecole = cleaned_data.get('ecole')
        matricule = (cleaned_data.get('matricule') or '').strip()
        nom = cleaned_data.get('nom')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Les deux mots de passe ne correspondent pas.")
        elif password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error('password1', exc)

        if not (profil and matricule and nom):
            return cleaned_data

        # Élève / professeur : l'établissement reste obligatoire.
        if profil != 'PARENT' and not ecole:
            self.add_error('ecole', "Sélectionnez votre établissement.")
            return cleaned_data

        cible = None
        if profil == 'PARENT':
            candidats = list(Tuteur.objects.filter(matricule__iexact=matricule))
            if len(candidats) > 1 and nom:
                # Désambiguïsation par le nom si plusieurs écoles partagent un matricule.
                filtrés = [t for t in candidats if _normalise(t.nom) == _normalise(nom)]
                if len(filtrés) == 1:
                    candidats = filtrés
            if len(candidats) > 1:
                self.add_error(
                    'matricule',
                    "Plusieurs fiches tuteur correspondent à ce matricule. "
                    "Contactez votre établissement.",
                )
                return cleaned_data
            cible = candidats[0] if candidats else None
            deja_lie = cible and Utilisateur.objects.filter(tuteur=cible).exists()
            label = "aucun tuteur"
        elif profil == 'ELEVE':
            cible = Eleve.objects.filter(ecole=ecole, matricule=matricule).first()
            deja_lie = cible and Utilisateur.objects.filter(eleve=cible).exists()
            label = "aucun élève"
        else:  # PROFESSEUR
            from grh.models import Personnel
            cible = Personnel.objects.filter(ecole=ecole, matricule=matricule).first()
            deja_lie = cible and cible.utilisateur_id is not None
            label = "aucun membre du personnel"

        if cible is None:
            if profil == 'PARENT':
                self.add_error(
                    'matricule',
                    "Il n'existe aucun tuteur avec ce matricule. "
                    "Vérifiez le matricule ou contactez votre école.",
                )
            else:
                self.add_error(
                    'matricule',
                    f"Il n'existe {label} avec ce matricule dans l'établissement sélectionné. "
                    "Vérifiez le matricule ou contactez votre école.",
                )
            return cleaned_data

        if _normalise(cible.nom) != _normalise(nom):
            self.add_error('nom', "Le nom saisi ne correspond pas à celui enregistré par l'école pour ce matricule.")
            return cleaned_data

        if deja_lie:
            self.add_error('matricule', "Un compte est déjà associé à ce matricule. Utilisez la page de connexion.")
            return cleaned_data

        self._cible = cible
        # Pour un parent, l'école est déduite de la fiche tuteur.
        if profil == 'PARENT':
            cleaned_data['ecole'] = cible.ecole
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        user = Utilisateur(
            username=data['username'],
            email=data.get('email', ''),
            prenom=data['prenom'],
            last_name=data['nom'],
            role=data['profil'],
            ecole=data.get('ecole'),
        )
        user.set_password(data['password1'])

        cible = getattr(self, '_cible', None)
        if data['profil'] == 'PARENT':
            user.tuteur = cible
            if cible is not None:
                user.ecole = cible.ecole
        elif data['profil'] == 'ELEVE':
            user.eleve = cible

        user.save()

        if data['profil'] == 'PROFESSEUR' and cible is not None:
            cible.utilisateur = user
            cible.save(update_fields=['utilisateur'])

        return user


class ProfilForm(FormControlMixin, forms.ModelForm):
    """Personnalisation du compte connecté."""

    telephone = forms.CharField(
        label="Téléphone",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ex: +243…'}),
    )

    class Meta:
        model = Utilisateur
        fields = ['prenom', 'last_name', 'email', 'avatar']
        labels = {
            'prenom': 'Prénom',
            'last_name': 'Nom',
            'email': 'Adresse e-mail',
            'avatar': 'Photo de profil',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'vous@exemple.com'}),
        }
        help_texts = {
            'email': 'Requis pour récupérer un mot de passe perdu.',
            'avatar': 'JPG ou PNG, de préférence carrée.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance
        initial_tel = ''
        if getattr(user, 'tuteur_id', None) and user.tuteur:
            initial_tel = user.tuteur.telephone or ''
        else:
            try:
                initial_tel = user.personnel.telephone or ''
            except Exception:
                initial_tel = ''
        self.fields['telephone'].initial = initial_tel
        self.fields['email'].required = False

    def save(self, commit=True):
        user = super().save(commit=commit)
        telephone = (self.cleaned_data.get('telephone') or '').strip()
        if not commit:
            return user

        if user.tuteur_id and user.tuteur:
            user.tuteur.telephone = telephone
            user.tuteur.save(update_fields=['telephone'])
        else:
            try:
                personnel = user.personnel
            except Exception:
                personnel = None
            if personnel is not None:
                personnel.telephone = telephone
                personnel.save(update_fields=['telephone'])
        return user


class ChangerMotDePasseForm(FormControlMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Mot de passe actuel'
        self.fields['new_password1'].label = 'Nouveau mot de passe'
        self.fields['new_password2'].label = 'Confirmer le nouveau mot de passe'


class MotDePasseOublieForm(FormControlMixin, PasswordResetForm):
    """Accepte un e-mail ou un identifiant de connexion."""

    email = forms.CharField(
        label='Identifiant ou e-mail',
        max_length=254,
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'placeholder': 'Votre identifiant ou adresse e-mail',
        }),
    )

    def get_users(self, email_or_username):
        value = (email_or_username or '').strip()
        if not value:
            return []
        actifs = Utilisateur.objects.filter(is_active=True).filter(
            Q(email__iexact=value) | Q(username__iexact=value)
        )
        return (
            u for u in actifs
            if u.has_usable_password() and (u.email or '').strip()
        )

    def clean_email(self):
        # Message identique que le compte existe ou non (anti-énumération).
        return self.cleaned_data['email'].strip()


class NouveauMotDePasseForm(FormControlMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Nouveau mot de passe'
        self.fields['new_password2'].label = 'Confirmer le nouveau mot de passe'
