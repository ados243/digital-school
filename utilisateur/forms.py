from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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
