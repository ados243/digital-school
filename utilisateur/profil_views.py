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
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import (
    ChangerMotDePasseForm,
    MotDePasseOublieForm,
    NouveauMotDePasseForm,
    ProfilForm,
)


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
    else:
        form = ProfilForm(instance=user)
        password_form = ChangerMotDePasseForm(user)

    return render(request, 'utilisateur/profil.html', {
        'form': form,
        'password_form': password_form,
        'base_template': base,
        'title': 'Mon profil',
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
