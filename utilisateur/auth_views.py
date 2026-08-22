"""Connexion sécurisée : verrouillage, MFA WhatsApp, vérification d'inscription."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .forms import ConnexionForm, InscriptionForm
from .security import (
    MSG_AUTH_GENERIQUE,
    MSG_CONTACT_MANQUANT,
    SESSION_MFA,
    SESSION_RESET,
    SESSION_SIGNUP,
    contact_telephone_fiche,
    doit_mfa,
    enregistrer_echec_connexion,
    envoyer_code_whatsapp,
    est_verrouille,
    fermer_session_connexion,
    generer_code,
    journaliser,
    masquer_telephone,
    notifier_nouvel_appareil,
    otp_encore_valide,
    ouvrir_session_connexion,
    payload_otp,
    reinitialiser_echecs,
    telephone_utilisateur,
    verifier_otp_session,
)

Utilisateur = get_user_model()


def _next_url(request, fallback='utilisateur:post_login'):
    nxt = request.POST.get('next') or request.GET.get('next') or ''
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return reverse(fallback)


class ConnexionView(LoginView):
    template_name = 'utilisateur/login.html'
    authentication_form = ConnexionForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        username = form.cleaned_data.get('username') or ''
        if est_verrouille(self.request, username):
            form.add_error(None, MSG_AUTH_GENERIQUE)
            return self.form_invalid(form)

        reinitialiser_echecs(self.request, username)

        if doit_mfa(user):
            tel = telephone_utilisateur(user)
            if not tel:
                form.add_error(
                    None,
                    "Aucun numéro WhatsApp n'est associé à ce compte. "
                    "Renseignez-le sur la fiche (personnel, tuteur) ou le téléphone de l'école.",
                )
                return self.form_invalid(form)

            code = generer_code()
            ok, err = envoyer_code_whatsapp(tel, code)
            self.request.session[SESSION_MFA] = payload_otp(code, extra={
                'user_id': user.pk,
                'backend': getattr(user, 'backend', None) or 'django.contrib.auth.backends.ModelBackend',
                'next': _next_url(self.request),
                'contact_masque': masquer_telephone(tel),
            })
            self.request.session.modified = True
            if ok:
                messages.info(
                    self.request,
                    f"Un code de vérification a été envoyé au WhatsApp {masquer_telephone(tel)}.",
                )
            else:
                journaliser(self.request, action='MFA_ENVOI_ECHEC', user=user, ressource='auth')
                messages.error(
                    self.request,
                    "L'envoi du code WhatsApp a échoué. Vérifiez le portefeuille Bird, "
                    "puis cliquez sur « Renvoyer le code ».",
                )
            return redirect('utilisateur:mfa')

        return self._finaliser_connexion(user)

    def form_invalid(self, form):
        username = (self.request.POST.get(form.add_prefix('username')) or '').strip()
        password = self.request.POST.get(form.add_prefix('password')) or ''
        if username and password and not est_verrouille(self.request, username):
            enregistrer_echec_connexion(self.request, username)
        if username and password:
            form.errors.pop('__all__', None)
            form.add_error(None, MSG_AUTH_GENERIQUE)
        return super().form_invalid(form)

    def _finaliser_connexion(self, user, via_mfa=False, backend=None):
        if backend:
            auth_login(self.request, user, backend=backend)
        else:
            auth_login(self.request, user)
        ouvrir_session_connexion(self.request, user, via_mfa=via_mfa)
        journaliser(self.request, action='CONNEXION', ressource='auth', user=user)
        notifier_nouvel_appareil(self.request, user)
        return redirect(_next_url(self.request))


@require_http_methods(['GET', 'POST'])
def mfa_view(request):
    pending = request.session.get(SESSION_MFA)
    if not pending or not otp_encore_valide(pending):
        request.session.pop(SESSION_MFA, None)
        messages.error(request, "La vérification a expiré. Reconnectez-vous.")
        return redirect('utilisateur:login')

    contact_masque = pending.get('contact_masque') or ''
    user = Utilisateur.objects.filter(pk=pending.get('user_id')).first()
    if user and not contact_masque:
        contact_masque = masquer_telephone(telephone_utilisateur(user))

    if request.method == 'POST':
        if request.POST.get('action') == 'renvoyer':
            return _renvoyer_mfa(request, user, pending)
        ok, err = verifier_otp_session(pending, request.POST.get('code') or '')
        request.session[SESSION_MFA] = pending
        request.session.modified = True
        if not ok:
            return render(request, 'utilisateur/mfa_verify.html', {
                'contact_masque': contact_masque,
                'erreur': err,
            })
        request.session.pop(SESSION_MFA, None)
        if not user or not user.is_active:
            messages.error(request, MSG_AUTH_GENERIQUE)
            return redirect('utilisateur:login')
        backend = pending.get('backend') or 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user, backend=backend)
        ouvrir_session_connexion(request, user, via_mfa=True)
        journaliser(request, action='MFA', ressource='auth', user=user)
        notifier_nouvel_appareil(request, user)
        nxt = pending.get('next') or reverse('utilisateur:post_login')
        if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
            nxt = reverse('utilisateur:post_login')
        return redirect(nxt)

    return render(request, 'utilisateur/mfa_verify.html', {
        'contact_masque': contact_masque,
        'erreur': '',
    })


def _renvoyer_mfa(request, user, pending):
    if not user:
        return redirect('utilisateur:login')
    tel = telephone_utilisateur(user)
    if not tel:
        messages.error(request, "Aucun numéro WhatsApp n'est associé à ce compte.")
        return redirect('utilisateur:mfa')
    code = generer_code()
    ok, _err = envoyer_code_whatsapp(tel, code)
    request.session[SESSION_MFA] = payload_otp(code, extra={
        'user_id': user.pk,
        'backend': pending.get('backend'),
        'next': pending.get('next'),
        'contact_masque': masquer_telephone(tel),
    })
    request.session.modified = True
    if ok:
        messages.success(request, "Un nouveau code a été envoyé par WhatsApp.")
    else:
        journaliser(request, action='MFA_ENVOI_ECHEC', user=user, ressource='auth')
        messages.error(request, "L'envoi du code WhatsApp a échoué. Réessayez plus tard.")
    return redirect('utilisateur:mfa')


def demarrer_verification_inscription(request, form):
    """Après validation : code WhatsApp, ou création directe si l'OTP est désactivé."""
    cible = getattr(form, '_cible', None)
    profil = form.cleaned_data.get('profil')
    ecole = form.cleaned_data.get('ecole')
    pending = {
        'profil': profil,
        'ecole_id': getattr(ecole, 'pk', None),
        'cible_id': getattr(cible, 'pk', None),
        'matricule': form.cleaned_data.get('matricule'),
        'nom': form.cleaned_data.get('nom'),
        'prenom': form.cleaned_data.get('prenom'),
        'email': form.cleaned_data.get('email') or '',
        'username': form.cleaned_data.get('username'),
        'password_hash': make_password(form.cleaned_data['password1']),
        'contact_masque': '',
    }

    if not getattr(settings, "INSCRIPTION_WHATSAPP_ACTIF", False):
        user = _creer_compte_depuis_session(pending)
        auth_login(request, user)
        ouvrir_session_connexion(request, user, via_mfa=False)
        journaliser(request, action='INSCRIPTION_COMPTE', ressource='auth', user=user)
        messages.success(request, f"Bienvenue {user.prenom} ! Votre compte a été créé avec succès.")
        return redirect('utilisateur:post_login')

    contact = contact_telephone_fiche(profil, cible)
    if not contact:
        form.add_error(None, MSG_CONTACT_MANQUANT)
        return render(request, 'utilisateur/inscription.html', {
            'form': form,
            'inscription_whatsapp_actif': True,
        })

    code = generer_code()
    ok, _err = envoyer_code_whatsapp(contact, code)
    if not ok:
        form.add_error(
            None,
            "L'envoi du code WhatsApp a échoué. Réessayez plus tard ou contactez l'établissement.",
        )
        return render(request, 'utilisateur/inscription.html', {
            'form': form,
            'inscription_whatsapp_actif': True,
        })
    pending['contact_masque'] = masquer_telephone(contact)
    request.session[SESSION_SIGNUP] = payload_otp(code, extra=pending)
    request.session.modified = True
    journaliser(request, action='INSCRIPTION_CODE', ressource='auth', extra={'profil': profil})
    messages.info(
        request,
        f"Un code de vérification a été envoyé au WhatsApp {masquer_telephone(contact)}.",
    )
    return redirect('utilisateur:verifier_compte')


@require_http_methods(['GET', 'POST'])
def verifier_compte_view(request):
    pending = request.session.get(SESSION_SIGNUP)
    if not pending or not otp_encore_valide(pending):
        request.session.pop(SESSION_SIGNUP, None)
        messages.error(request, "La vérification a expiré. Recommencez la création de compte.")
        return redirect('utilisateur:inscription')

    if request.method == 'POST':
        if request.POST.get('action') == 'renvoyer':
            return _renvoyer_signup(request, pending)
        ok, err = verifier_otp_session(pending, request.POST.get('code') or '')
        request.session[SESSION_SIGNUP] = pending
        request.session.modified = True
        if not ok:
            return render(request, 'utilisateur/verification_compte.html', {
                'contact_masque': pending.get('contact_masque') or '',
                'erreur': err,
            })
        user = _creer_compte_depuis_session(pending)
        request.session.pop(SESSION_SIGNUP, None)
        auth_login(request, user)
        ouvrir_session_connexion(request, user, via_mfa=True)
        journaliser(request, action='INSCRIPTION_COMPTE', ressource='auth', user=user)
        messages.success(request, f"Bienvenue {user.prenom} ! Votre compte a été créé avec succès.")
        return redirect('utilisateur:post_login')

    return render(request, 'utilisateur/verification_compte.html', {
        'contact_masque': pending.get('contact_masque') or '',
        'erreur': '',
    })


def _renvoyer_signup(request, pending):
    cible = _cible_depuis_pending(pending)
    contact = contact_telephone_fiche(pending.get('profil'), cible)
    if not contact:
        messages.error(request, MSG_CONTACT_MANQUANT)
        return redirect('utilisateur:inscription')
    code = generer_code()
    ok, _err = envoyer_code_whatsapp(contact, code)
    if not ok:
        messages.error(request, "L'envoi du code WhatsApp a échoué. Réessayez plus tard.")
        return redirect('utilisateur:verifier_compte')
    request.session[SESSION_SIGNUP] = payload_otp(code, extra={
        'profil': pending.get('profil'),
        'ecole_id': pending.get('ecole_id'),
        'cible_id': pending.get('cible_id'),
        'matricule': pending.get('matricule'),
        'nom': pending.get('nom'),
        'prenom': pending.get('prenom'),
        'email': pending.get('email') or '',
        'username': pending.get('username'),
        'password_hash': pending.get('password_hash'),
        'contact_masque': masquer_telephone(contact),
    })
    request.session.modified = True
    messages.success(request, "Un nouveau code a ete envoye par WhatsApp.")
    return redirect('utilisateur:verifier_compte')


def _cible_depuis_pending(pending):
    profil = pending.get('profil')
    cible_id = pending.get('cible_id')
    ecole_id = pending.get('ecole_id')
    if not cible_id:
        return None
    if profil == 'PARENT':
        from inscription.models import Tuteur
        return Tuteur.objects.filter(pk=cible_id).select_related('ecole').first()
    if profil == 'ELEVE':
        from inscription.models import Eleve
        return Eleve.objects.filter(pk=cible_id, ecole_id=ecole_id).select_related('titeur', 'ecole').first()
    from grh.models import Personnel
    return Personnel.objects.filter(pk=cible_id, ecole_id=ecole_id).first()


def _creer_compte_depuis_session(pending):
    from inscription.models import Ecole

    cible = _cible_depuis_pending(pending)
    ecole = Ecole.objects.filter(pk=pending.get('ecole_id')).first()
    user = Utilisateur(
        username=pending['username'],
        email=pending.get('email') or '',
        prenom=pending.get('prenom') or '',
        last_name=pending.get('nom') or '',
        role=pending['profil'],
        ecole=ecole,
        password=pending['password_hash'],
    )
    if pending.get('profil') == 'PARENT':
        user.tuteur = cible
        if cible is not None:
            user.ecole = cible.ecole
    elif pending.get('profil') == 'ELEVE':
        user.eleve = cible
    user.save()
    if pending.get('profil') == 'PROFESSEUR' and cible is not None:
        cible.utilisateur = user
        cible.save(update_fields=['utilisateur'])
    return user


def mot_de_passe_oublie_view(request):
    from .forms import MotDePasseOublieForm

    if request.user.is_authenticated:
        return redirect('utilisateur:post_login')
    form = MotDePasseOublieForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        identifiant = form.cleaned_data['email']
        user = Utilisateur.objects.filter(
            is_active=True, username__iexact=identifiant
        ).first()
        if user and user.has_usable_password():
            tel = telephone_utilisateur(user)
            if tel:
                code = generer_code()
                ok, _err = envoyer_code_whatsapp(tel, code)
                if ok:
                    request.session[SESSION_RESET] = payload_otp(code, extra={
                        'user_id': user.pk,
                        'contact_masque': masquer_telephone(tel),
                    })
                    request.session.modified = True
                else:
                    journaliser(request, action='RESET_ENVOI_ECHEC', ressource='auth')
        return redirect('utilisateur:password_reset_done')
    return render(request, 'utilisateur/password_reset_form.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def mot_de_passe_oublie_code_view(request):
    pending = request.session.get(SESSION_RESET)
    if not pending or not otp_encore_valide(pending):
        request.session.pop(SESSION_RESET, None)
        return render(request, 'utilisateur/password_reset_done.html')

    contact_masque = pending.get('contact_masque') or ''
    if request.method == 'POST':
        if request.POST.get('action') == 'renvoyer':
            user = Utilisateur.objects.filter(pk=pending.get('user_id')).first()
            tel = telephone_utilisateur(user)
            if user and tel:
                code = generer_code()
                ok, _err = envoyer_code_whatsapp(tel, code)
                if ok:
                    request.session[SESSION_RESET] = payload_otp(code, extra={
                        'user_id': user.pk,
                        'contact_masque': masquer_telephone(tel),
                    })
                    request.session.modified = True
                    messages.success(request, "Un nouveau code a été envoyé par WhatsApp.")
                else:
                    journaliser(request, action='RESET_ENVOI_ECHEC', ressource='auth')
                    messages.error(request, "L'envoi du code WhatsApp a échoué. Réessayez plus tard.")
            return redirect('utilisateur:password_reset_done')
        ok, err = verifier_otp_session(pending, request.POST.get('code') or '')
        request.session[SESSION_RESET] = pending
        request.session.modified = True
        if not ok:
            return render(request, 'utilisateur/verification_compte.html', {
                'contact_masque': contact_masque,
                'erreur': err,
                'mode_reset': True,
            })
        pending['verified'] = True
        request.session[SESSION_RESET] = pending
        request.session.modified = True
        return redirect('utilisateur:password_reset_confirm')
    return render(request, 'utilisateur/verification_compte.html', {
        'contact_masque': contact_masque,
        'erreur': '',
        'mode_reset': True,
    })


@require_http_methods(['GET', 'POST'])
def mot_de_passe_nouveau_view(request):
    from .forms import NouveauMotDePasseForm

    pending = request.session.get(SESSION_RESET) or {}
    if not pending.get('verified'):
        messages.error(request, "La verification a expire. Recommencez.")
        return redirect('utilisateur:password_reset')
    user = Utilisateur.objects.filter(pk=pending.get('user_id'), is_active=True).first()
    if not user:
        request.session.pop(SESSION_RESET, None)
        return redirect('utilisateur:password_reset')
    form = NouveauMotDePasseForm(user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        request.session.pop(SESSION_RESET, None)
        messages.success(request, "Votre mot de passe a ete mis a jour.")
        return redirect('utilisateur:password_reset_complete')
    return render(request, 'utilisateur/password_reset_confirm.html', {
        'form': form,
        'validlink': True,
    })


@require_http_methods(['GET', 'POST'])
def logout_view(request):
    if request.user.is_authenticated:
        fermer_session_connexion(request)
        journaliser(request, action='DECONNEXION', ressource='auth', user=request.user)
        auth_logout(request)
    return redirect('utilisateur:login')
