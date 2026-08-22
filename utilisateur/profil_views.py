"""Profil utilisateur et gestion des mots de passe."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from .forms import (
    ChangerMotDePasseForm,
    MotDePasseOublieForm,
    NouveauMotDePasseForm,
    ProfilForm,
)
from .models import SessionConnexion
from .security import SESSION_CONNEXION_ID, cloturer_sessions_inactives, revoquer_session_connexion


def _base_template_for(user):
    if (
        getattr(user, 'is_parent', False)
        or getattr(user, 'is_eleve', False)
        or getattr(user, 'is_professeur', False)
    ):
        return 'portal_base.html'
    return 'base.html'


@login_required
def profil_view(request):
    user = request.user
    base = _base_template_for(user)
    session_courante_id = request.session.get(SESSION_CONNEXION_ID)

    if request.method == 'POST' and request.POST.get('action') == 'profil':
        form = ProfilForm(request.POST, request.FILES, instance=user)
        password_form = ChangerMotDePasseForm(user)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre profil a été mis à jour.")
            return redirect('utilisateur:profil')
    elif request.method == 'POST' and request.POST.get('action') == 'password':
        form = ProfilForm(instance=user)
        password_form = ChangerMotDePasseForm(user, request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Votre mot de passe a été modifié.")
            return redirect('utilisateur:profil')
    elif request.method == 'POST' and request.POST.get('action') == 'revoquer_session':
        form = ProfilForm(instance=user)
        password_form = ChangerMotDePasseForm(user)
        session_obj = get_object_or_404(
            SessionConnexion,
            pk=request.POST.get('session_id'),
            utilisateur=user,
        )
        if session_obj.pk == session_courante_id:
            messages.error(
                request,
                "Vous ne pouvez pas révoquer la session en cours ici. Utilisez Déconnexion.",
            )
        else:
            revoquer_session_connexion(session_obj)
            messages.success(request, "La session a été fermée.")
            return redirect('utilisateur:profil')
    elif request.method == 'POST' and request.POST.get('action') == 'revoquer_autres':
        form = ProfilForm(instance=user)
        password_form = ChangerMotDePasseForm(user)
        autres = SessionConnexion.objects.filter(
            utilisateur=user,
            ended_at__isnull=True,
        ).exclude(pk=session_courante_id or 0)
        for session_obj in autres:
            revoquer_session_connexion(session_obj)
        messages.success(request, "Les autres sessions ont été fermées.")
        return redirect('utilisateur:profil')
    else:
        form = ProfilForm(instance=user)
        password_form = ChangerMotDePasseForm(user)

    cloturer_sessions_inactives(utilisateur=user)
    sessions = SessionConnexion.objects.filter(utilisateur=user)[:30]
    autres_actives = any(
        s.est_active and s.pk != session_courante_id for s in sessions
    )

    return render(request, 'utilisateur/profil.html', {
        'form': form,
        'password_form': password_form,
        'base_template': base,
        'title': 'Mon profil',
        'sessions_connexion': sessions,
        'session_courante_id': session_courante_id,
        'autres_sessions_actives': autres_actives,
    })


class MotDePasseOublieView(PasswordResetView):
    template_name = 'utilisateur/password_reset_form.html'
    email_template_name = 'utilisateur/password_reset_email.txt'
    html_email_template_name = 'utilisateur/password_reset_email.html'
    subject_template_name = 'utilisateur/password_reset_subject.txt'
    form_class = MotDePasseOublieForm
    success_url = reverse_lazy('utilisateur:password_reset_done')
    extra_email_context = {'site_name': 'Digital School'}


class MotDePasseOublieDoneView(PasswordResetDoneView):
    template_name = 'utilisateur/password_reset_done.html'


class MotDePasseResetConfirmView(PasswordResetConfirmView):
    template_name = 'utilisateur/password_reset_confirm.html'
    form_class = NouveauMotDePasseForm
    success_url = reverse_lazy('utilisateur:password_reset_complete')


class MotDePasseResetCompleteView(PasswordResetCompleteView):
    template_name = 'utilisateur/password_reset_complete.html'
