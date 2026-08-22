"""Ressources partagées — espace enseignant (déposer) et élève (consulter)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from inscription.models import Annee_Scolaire
from pedagogie.forms import RessourcePartageeForm
from pedagogie.models import RessourcePartagee
from utilisateur.cours_views import _require_eleve
from utilisateur.travaux_views import (
    _classes_enseignant,
    _matieres_enseignant,
    _require_enseignant,
)


def _ressources_enseignant_qs(personnel):
    return (
        RessourcePartagee.objects.filter(ecole=personnel.ecole, enseignant=personnel)
        .select_related('matiere', 'enseignant', 'annee_scolaire')
        .prefetch_related('classes')
        .order_by('-created_at')
    )


def _peut_gerer_ressource(personnel, ressource):
    return (
        personnel
        and ressource.ecole_id == personnel.ecole_id
        and ressource.enseignant_id == personnel.id
    )


def _classes_autorisees(personnel, classes):
    ids = set(_classes_enseignant(personnel).values_list('id', flat=True))
    return all(c.id in ids for c in (classes or []))


@login_required
def ressource_enseignant_list(request):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    ressources = list(_ressources_enseignant_qs(personnel))
    classe_id = request.GET.get('classe')
    type_fichier = request.GET.get('type')
    if classe_id:
        ressources = [r for r in ressources if r.concerne_classe(classe_id)]
    if type_fichier:
        ressources = [r for r in ressources if r.type_fichier == type_fichier]

    return render(request, 'utilisateur/ressource_enseignant_list.html', {
        'ressources': ressources,
        'classes': _classes_enseignant(personnel),
        'filtre_classe': classe_id or '',
        'filtre_type': type_fichier or '',
        'types': RessourcePartagee.TYPE_CHOICES,
        'nb_publiees': sum(1 for r in ressources if r.publie),
        'nb_brouillons': sum(1 for r in ressources if not r.publie),
    })


def _enregistrer_ressource(request, personnel, instance=None):
    ecole = personnel.ecole
    classes_qs = _classes_enseignant(personnel)
    matieres_qs = _matieres_enseignant(personnel)
    if request.method == 'POST':
        form = RessourcePartageeForm(
            request.POST,
            request.FILES,
            instance=instance,
            ecole=ecole,
            classes_qs=classes_qs,
            matieres_qs=matieres_qs,
        )
        if form.is_valid():
            classes = list(form.cleaned_data.get('classes') or [])
            if not _classes_autorisees(personnel, classes):
                messages.error(request, "Vous ne pouvez pas partager un fichier avec ces classes.")
            else:
                ressource = form.save(commit=False)
                ressource.ecole = ecole
                ressource.enseignant = personnel
                ressource.save()
                form.save_m2m()
                messages.success(
                    request,
                    "Ressource mise à jour." if instance else "Ressource partagée avec les classes sélectionnées.",
                )
                return None, redirect('utilisateur:ressource_enseignant_list')
    else:
        initial = {}
        if not instance:
            annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
            if annee:
                initial['annee_scolaire'] = annee
            if request.GET.get('classe'):
                initial['classes'] = [request.GET.get('classe')]
            if request.GET.get('matiere'):
                initial['matiere'] = request.GET.get('matiere')
        form = RessourcePartageeForm(
            instance=instance,
            ecole=ecole,
            classes_qs=classes_qs,
            matieres_qs=matieres_qs,
            initial=initial or None,
        )
    return form, None


@login_required
def ressource_enseignant_create(request):
    personnel, err = _require_enseignant(request)
    if err:
        return err
    form, redir = _enregistrer_ressource(request, personnel)
    if redir:
        return redir
    return render(request, 'utilisateur/ressource_enseignant_form.html', {
        'form': form,
        'title': 'Partager une ressource',
        'ressource': None,
    })


@login_required
def ressource_enseignant_update(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err
    ressource = get_object_or_404(
        RessourcePartagee.objects.prefetch_related('classes'),
        pk=pk,
        ecole=personnel.ecole,
    )
    if not _peut_gerer_ressource(personnel, ressource):
        messages.error(request, "Vous n'avez pas accès à cette ressource.")
        return redirect('utilisateur:ressource_enseignant_list')
    form, redir = _enregistrer_ressource(request, personnel, instance=ressource)
    if redir:
        return redir
    return render(request, 'utilisateur/ressource_enseignant_form.html', {
        'form': form,
        'title': 'Modifier la ressource',
        'ressource': ressource,
    })


@login_required
def ressource_enseignant_delete(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err
    ressource = get_object_or_404(
        RessourcePartagee.objects.prefetch_related('classes'),
        pk=pk,
        ecole=personnel.ecole,
    )
    if not _peut_gerer_ressource(personnel, ressource):
        messages.error(request, "Vous n'avez pas accès à cette ressource.")
        return redirect('utilisateur:ressource_enseignant_list')
    if request.method == 'POST':
        ressource.delete()
        messages.success(request, "Ressource supprimée.")
        return redirect('utilisateur:ressource_enseignant_list')
    return render(request, 'utilisateur/ressource_enseignant_confirm_delete.html', {
        'ressource': ressource,
    })


def _ressources_eleve_qs(inscription):
    return (
        RessourcePartagee.objects.filter(
            publie=True,
            ecole=inscription.eleve.ecole,
            annee_scolaire=inscription.annee_s,
            classes=inscription.classe,
        )
        .select_related('matiere', 'enseignant', 'annee_scolaire')
        .prefetch_related('classes')
        .distinct()
        .order_by('-created_at')
    )


@login_required
def ressource_eleve_list(request):
    eleve, inscription, err = _require_eleve(request)
    if err:
        return err

    ressources = list(_ressources_eleve_qs(inscription))
    type_fichier = request.GET.get('type')
    if type_fichier:
        ressources = [r for r in ressources if r.type_fichier == type_fichier]

    return render(request, 'utilisateur/ressource_eleve_list.html', {
        'inscription': inscription,
        'ressources': ressources,
        'filtre_type': type_fichier or '',
        'types': RessourcePartagee.TYPE_CHOICES,
    })


@login_required
def ressource_eleve_detail(request, pk):
    eleve, inscription, err = _require_eleve(request)
    if err:
        return err
    ressource = get_object_or_404(
        _ressources_eleve_qs(inscription).filter(pk=pk)
    )
    return render(request, 'utilisateur/ressource_eleve_detail.html', {
        'inscription': inscription,
        'ressource': ressource,
    })
