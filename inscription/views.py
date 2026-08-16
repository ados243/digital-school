from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.urls import reverse
from .models import Eleve, Inscription, Classe, Annee_Scolaire, Quartier
from .forms import EleveForm, TuteurForm, InscriptionForm, ClasseForm, QuartierForm
from .tenant import (
    get_user_ecole,
    eleves_for_ecole,
    tuteurs_for_ecole,
    inscriptions_for_ecole,
    classes_for_ecole,
    annees_for_ecole,
)


def _tuteur_payload(tuteur):
    nom_complet = f"{tuteur.prenom} {tuteur.nom} {tuteur.Post_nom}".strip()
    return {
        "id": tuteur.id,
        "nom": nom_complet,
        "matricule": tuteur.matricule,
        "telephone": tuteur.telephone or "",
        "label": f"{nom_complet} · {tuteur.matricule}".strip(),
    }


def _quartier_payload(quartier):
    commune = getattr(quartier.commune, "commune", "") if quartier.commune_id else ""
    label = f"{quartier.quartier} ({commune})" if commune else quartier.quartier
    return {
        "id": quartier.id,
        "quartier": quartier.quartier,
        "commune": commune,
        "label": label,
    }


def _is_ajax(request):
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "")
    )


def _classe_stats(classe, annee=None):
    """Retourne inscrits, pourcentage et statut complet pour une classe."""
    inscrits = classe.inscrits_annee_en_cours(annee)
    percent = int((inscrits / classe.capacite_max) * 100) if classe.capacite_max > 0 else 0
    return {
        'obj': classe,
        'inscrits': inscrits,
        'percent': percent,
        'is_full': inscrits >= classe.capacite_max,
    }


@login_required
def dashboard(request):
    ecole = get_user_ecole(request)
    eleves_qs = eleves_for_ecole(ecole)
    inscriptions_qs = inscriptions_for_ecole(ecole)
    classes_qs = classes_for_ecole(ecole)

    recent_inscriptions = inscriptions_qs.select_related('eleve', 'classe').order_by('-date', '-id')[:5]

    context = {
        'total_eleves': eleves_qs.count(),
        'total_inscriptions': inscriptions_qs.count(),
        'total_classes': classes_qs.count(),
        'garcons': eleves_qs.filter(sexe='Masculin').count(),
        'filles': eleves_qs.filter(sexe='Feminin').count(),
        'recent_eleves': eleves_qs.order_by('-id')[:5],
        'recent_inscriptions': recent_inscriptions,
        'total_capacity': sum(c.capacite_max for c in classes_qs),
    }
    return render(request, 'inscription/dashboard.html', context)


@login_required
def tuteur_create(request):
    ecole = get_user_ecole(request)
    form_prefix = (
        "tuteur_modal"
        if request.method == "POST"
        and any(k.startswith("tuteur_modal-") for k in request.POST)
        else None
    )
    if request.method == 'POST':
        form = TuteurForm(request.POST, prefix=form_prefix)
        if form.is_valid():
            tuteur = form.save(commit=False)
            tuteur.ecole = ecole
            tuteur.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True, "tuteur": _tuteur_payload(tuteur)})
            messages.success(request, f"Tuteur {tuteur.nom} enregistré avec succès.")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('inscription:eleve_list')
        if _is_ajax(request):
            errors = {
                field: [str(e) for e in errs]
                for field, errs in form.errors.items()
            }
            return JsonResponse({"ok": False, "errors": errors}, status=400)
    else:
        form = TuteurForm()
    return render(
        request,
        'inscription/tuteur_form.html',
        {
            'form': form,
            'quartier_form': QuartierForm(prefix='quartier_modal'),
            'quartier_create_url': reverse('inscription:quartier_create'),
        },
    )


@login_required
def quartier_create(request):
    """Création AJAX d'un quartier depuis le formulaire parent / tuteur."""
    form_prefix = (
        "quartier_modal"
        if request.method == "POST"
        and any(k.startswith("quartier_modal-") for k in request.POST)
        else None
    )
    if request.method != "POST":
        return redirect("inscription:tuteur_create")

    form = QuartierForm(request.POST, prefix=form_prefix)
    if form.is_valid():
        quartier = form.save()
        if _is_ajax(request):
            return JsonResponse({"ok": True, "quartier": _quartier_payload(quartier)})
        messages.success(request, f"Quartier « {quartier.quartier} » créé.")
        return redirect("inscription:tuteur_create")

    if _is_ajax(request):
        errors = {
            field: [str(e) for e in errs] for field, errs in form.errors.items()
        }
        return JsonResponse({"ok": False, "errors": errors}, status=400)
    messages.error(request, "Impossible de créer le quartier.")
    return redirect("inscription:tuteur_create")


@login_required
def eleve_list(request):
    ecole = get_user_ecole(request)
    query = request.GET.get('q', '')
    eleves = eleves_for_ecole(ecole).select_related(
        'titeur', 'titeur__quartier', 'titeur__quartier__commune'
    )
    if query:
        eleves = eleves.filter(
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(matricule__icontains=query)
        )

    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    eleves_inscrits_ids = set()
    if annee:
        eleves_inscrits_ids = set(
            inscriptions_for_ecole(ecole)
            .filter(annee_s=annee, eleve_id__in=eleves.values_list('id', flat=True))
            .values_list('eleve_id', flat=True)
        )

    return render(
        request,
        'inscription/eleve_list.html',
        {
            'eleves': eleves,
            'query': query,
            'eleves_inscrits_ids': eleves_inscrits_ids,
            'annee_courante': annee,
        },
    )


@login_required
def eleve_create(request):
    ecole = get_user_ecole(request)
    if request.method == 'POST':
        form = EleveForm(request.POST, request.FILES, ecole=ecole)
        if form.is_valid():
            eleve = form.save(commit=False)
            eleve.ecole = ecole
            eleve.save()
            messages.success(request, f"Élève {eleve.prenom} {eleve.nom} créé avec succès.")
            return redirect('inscription:eleve_list')
    else:
        form = EleveForm(ecole=ecole)

    context = _eleve_form_context(ecole, form, title="Créer la fiche de l'élève")
    return render(request, 'inscription/eleve_form.html', context)


@login_required
def eleve_update(request, pk):
    ecole = get_user_ecole(request)
    eleve = get_object_or_404(Eleve, pk=pk, ecole=ecole)
    if request.method == 'POST':
        form = EleveForm(request.POST, request.FILES, instance=eleve, ecole=ecole)
        if form.is_valid():
            form.save()
            messages.success(request, f"Fiche de l'élève {eleve.prenom} mise à jour.")
            return redirect('inscription:eleve_list')
    else:
        form = EleveForm(instance=eleve, ecole=ecole)
    context = _eleve_form_context(
        ecole, form, title="Modifier la fiche de l'élève", eleve=eleve
    )
    return render(request, 'inscription/eleve_form.html', context)


def _eleve_form_context(ecole, form, title, eleve=None):
    tuteurs_qs = tuteurs_for_ecole(ecole).order_by('nom', 'prenom')
    tuteurs_data = [_tuteur_payload(t) for t in tuteurs_qs]
    return {
        'form': form,
        'title': title,
        'eleve': eleve,
        'tuteurs_count': tuteurs_qs.count(),
        'tuteurs_data': tuteurs_data,
        'tuteur_form': TuteurForm(prefix='tuteur_modal'),
        'tuteur_create_url': reverse('inscription:tuteur_create'),
        'quartier_form': QuartierForm(prefix='quartier_modal'),
        'quartier_create_url': reverse('inscription:quartier_create'),
    }

@login_required
def eleve_delete(request, pk):
    ecole = get_user_ecole(request)
    eleve = get_object_or_404(Eleve, pk=pk, ecole=ecole)
    if request.method == 'POST':
        eleve.delete()
        messages.success(request, "Fiche de l'élève supprimée.")
        return redirect('inscription:eleve_list')
    return render(request, 'inscription/eleve_confirm_delete.html', {'eleve': eleve})


@login_required
def inscription_list(request):
    ecole = get_user_ecole(request)
    inscriptions = (
        inscriptions_for_ecole(ecole)
        .select_related('eleve', 'classe', 'annee_s')
        .order_by('-date', '-id')
    )
    return render(request, 'inscription/inscription_list.html', {'inscriptions': inscriptions})


def _inscription_form_context(request, ecole, form, is_update=False, ins=None, eleves_disponibles=None):
    annee_courante = annees_for_ecole(ecole).filter(est_encoure=True).first()
    classes_qs = classes_for_ecole(ecole).select_related('section')

    if eleves_disponibles is None:
        eleves_disponibles = eleves_for_ecole(ecole)
        if annee_courante and not is_update:
            eleves_disponibles = eleves_disponibles.exclude(
                id__in=inscriptions_for_ecole(ecole)
                .filter(annee_s=annee_courante)
                .values_list('eleve_id', flat=True)
            )

    eleves_data = [
        {
            'id': e.id,
            'nom': f"{e.prenom} {e.nom} {e.Post_nom}".strip(),
            'matricule': e.matricule,
            'sexe': e.get_sexe_display(),
            'label': f"{e.prenom} {e.nom} {e.Post_nom} · {e.matricule}".strip(),
        }
        for e in eleves_disponibles.order_by('nom', 'prenom')
    ]

    classes_data = {}
    for c in classes_qs:
        inscrits = c.inscrits_annee_en_cours(annee_courante) if annee_courante else 0
        places = max(c.capacite_max - inscrits, 0)
        classes_data[str(c.id)] = {
            'label': f"{c.classe} — {c.section}",
            'salle': c.salle,
            'capacite_max': c.capacite_max,
            'inscrits': inscrits,
            'places_restantes': places,
            'est_complete': inscrits >= c.capacite_max,
        }

    return {
        'form': form,
        'is_update': is_update,
        'ins': ins,
        'eleves_data': eleves_data,
        'classes_data': classes_data,
        'eleves_count': len(eleves_data) if not is_update else eleves_for_ecole(ecole).count(),
        'classes_count': classes_qs.count(),
        'annees_count': annees_for_ecole(ecole).count(),
        'annee_courante': annee_courante,
        'can_submit': is_update or (len(eleves_data) > 0 and classes_qs.exists() and annees_for_ecole(ecole).exists()),
    }


@login_required
def inscription_create(request):
    ecole = get_user_ecole(request)
    annee_courante = annees_for_ecole(ecole).filter(est_encoure=True).first()

    if request.method == 'POST':
        form = InscriptionForm(request.POST, ecole=ecole)
        if form.is_valid():
            ins = form.save()
            messages.success(
                request,
                f"Inscription de {ins.eleve.prenom} validée avec succès pour la classe de {ins.classe}.",
            )
            return redirect('inscription:inscription_list')
    else:
        eleves_disponibles = eleves_for_ecole(ecole)
        if annee_courante:
            eleves_disponibles = eleves_disponibles.exclude(
                id__in=inscriptions_for_ecole(ecole)
                .filter(annee_s=annee_courante)
                .values_list('eleve_id', flat=True)
            )

        initial_data = {}
        eleve_id = request.GET.get('eleve')
        if eleve_id:
            eleve = get_object_or_404(Eleve, id=eleve_id, ecole=ecole)
            if eleve in eleves_disponibles:
                initial_data['eleve'] = eleve
        if annee_courante:
            initial_data['annee_s'] = annee_courante

        form = InscriptionForm(initial=initial_data, ecole=ecole)
        form.fields['eleve'].queryset = eleves_disponibles

    eleves_disponibles = eleves_for_ecole(ecole)
    if annee_courante:
        eleves_disponibles = eleves_disponibles.exclude(
            id__in=inscriptions_for_ecole(ecole)
            .filter(annee_s=annee_courante)
            .values_list('eleve_id', flat=True)
        )
    form.fields['eleve'].queryset = eleves_disponibles

    context = _inscription_form_context(
        request, ecole, form, is_update=False, eleves_disponibles=eleves_disponibles
    )
    return render(request, 'inscription/inscription_form.html', context)


@login_required
def inscription_update(request, pk):
    ecole = get_user_ecole(request)
    ins = get_object_or_404(Inscription, pk=pk, classe__ecole=ecole)
    if request.method == 'POST':
        form = InscriptionForm(request.POST, instance=ins, ecole=ecole)
        if form.is_valid():
            form.save()
            messages.success(request, "Détails de l'inscription mis à jour.")
            return redirect('inscription:inscription_list')
    else:
        form = InscriptionForm(instance=ins, ecole=ecole)
    context = _inscription_form_context(request, ecole, form, is_update=True, ins=ins)
    return render(request, 'inscription/inscription_form.html', context)


@login_required
def classe_list(request):
    ecole = get_user_ecole(request)
    annee = annees_for_ecole(ecole).filter(est_encoure=True).first()
    classes = (
        classes_for_ecole(ecole)
        .select_related('section', 'ecole', 'titulaire')
        .order_by('section__section', 'classe')
    )
    classes_list = [_classe_stats(c, annee) for c in classes]
    return render(request, 'inscription/classe_list.html', {
        'classes': classes_list,
        'annee_courante': annee,
    })


@login_required
def classe_detail(request, pk):
    ecole = get_user_ecole(request)
    classe = get_object_or_404(
        Classe.objects.select_related('section__cycle', 'ecole', 'titulaire'),
        pk=pk,
        ecole=ecole,
    )
    annee = annees_for_ecole(ecole).filter(est_encoure=True).first()
    stats = _classe_stats(classe, annee)

    if annee:
        inscriptions = (
            inscriptions_for_ecole(ecole)
            .filter(classe=classe, annee_s=annee)
            .select_related('eleve')
            .order_by('eleve__nom', 'eleve__prenom')
        )
    else:
        inscriptions = Inscription.objects.none()

    from pedagogie.models import Matiere
    from pedagogie.views import _recap_eleves_presence

    matieres = Matiere.objects.filter(ecole=ecole, section=classe.section).order_by('libelle')
    total_coefficient = matieres.aggregate(total=Sum('coefficient'))['total'] or 0

    eleves_rows, jours_appeles, presence_totaux, taux_classe = _recap_eleves_presence(
        classe, annee, inscriptions
    )

    context = {
        'classe': classe,
        'stats': stats,
        'annee_courante': annee,
        'inscriptions': inscriptions,
        'eleves_rows': eleves_rows,
        'matieres': matieres,
        'total_coefficient': total_coefficient,
        'garcons': inscriptions.filter(eleve__sexe='Masculin').count(),
        'filles': inscriptions.filter(eleve__sexe='Feminin').count(),
        'places_restantes': max(classe.capacite_max - stats['inscrits'], 0),
        'jours_appeles': jours_appeles,
        'presence_totaux': presence_totaux,
        'taux_classe': taux_classe,
    }
    return render(request, 'inscription/classe_detail.html', context)


@login_required
def classe_create(request):
    ecole = get_user_ecole(request)
    if request.method == 'POST':
        form = ClasseForm(request.POST, ecole=ecole)
        if form.is_valid():
            c = form.save(commit=False)
            c.ecole = ecole
            c.save()
            messages.success(request, f"Classe de {c.classe} créée avec succès.")
            next_url = request.GET.get('next', 'inscription:classe_list')
            return redirect(next_url)
    else:
        form = ClasseForm(ecole=ecole)
    return render(request, 'inscription/classe_form.html', {
        'form': form,
        'cancel_url': request.GET.get('next'),
        'enseignants_count': form.fields['titulaire'].queryset.count(),
    })


@login_required
def classe_update(request, pk):
    ecole = get_user_ecole(request)
    classe = get_object_or_404(Classe, pk=pk, ecole=ecole)
    if request.method == 'POST':
        form = ClasseForm(request.POST, instance=classe, ecole=ecole)
        if form.is_valid():
            form.save()
            messages.success(request, f"Classe de {classe.classe} mise à jour.")
            next_url = request.GET.get('next', 'inscription:classe_list')
            return redirect(next_url)
    else:
        form = ClasseForm(instance=classe, ecole=ecole)
    return render(request, 'inscription/classe_form.html', {
        'form': form,
        'classe': classe,
        'is_update': True,
        'cancel_url': request.GET.get('next'),
        'enseignants_count': form.fields['titulaire'].queryset.count(),
    })


@login_required
def classe_delete(request, pk):
    ecole = get_user_ecole(request)
    classe = get_object_or_404(Classe, pk=pk, ecole=ecole)
    inscrits = classe.inscrits_annee_en_cours()
    if request.method == 'POST':
        if inscrits > 0:
            messages.error(
                request,
                f"Impossible de supprimer la classe {classe.classe} : {inscrits} élève(s) inscrit(s) cette année.",
            )
            return redirect('inscription:classe_list')
        name = classe.classe
        classe.delete()
        messages.success(request, f"Classe de {name} supprimée avec succès.")
        return redirect('inscription:classe_list')
    return render(request, 'inscription/classe_confirm_delete.html', {
        'classe': classe,
        'inscrits': inscrits,
    })
