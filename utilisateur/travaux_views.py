"""Travaux cotés — espace enseignant (titulaire / matières affectées)."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from inscription.models import Annee_Scolaire, Classe, Inscription
from pedagogie.affectations import peut_gerer_matiere_classe, travaux_accessibles_qs
from pedagogie.forms import TravailCoteForm
from pedagogie.models import AffectationEnseignement, Matiere, NoteEleve, TravailCote
from pedagogie.signals import suspendre_actualisation_bulletins
from pedagogie.bulletin import actualiser_bulletins_inscriptions


def _personnel(user):
    from grh.models import Personnel
    return Personnel.objects.filter(utilisateur=user).select_related('ecole').first()


def _require_enseignant(request):
    if not request.user.is_professeur:
        return None, redirect('utilisateur:post_login')
    personnel = _personnel(request.user)
    if not personnel:
        messages.warning(request, "Aucune fiche personnel n'est rattachée à votre compte.")
        return None, redirect('utilisateur:enseignant_dashboard')
    return personnel, None


def _travaux_qs(personnel):
    return travaux_accessibles_qs(
        personnel,
        TravailCote.objects.filter(ecole=personnel.ecole)
        .select_related('matiere', 'classe', 'annee_scolaire', 'periode', 'division'),
    )


def _classes_enseignant(personnel):
    aff_classes = AffectationEnseignement.objects.filter(
        enseignant=personnel, ecole=personnel.ecole
    ).values_list('classe_id', flat=True)
    sections_matieres = Matiere.objects.filter(
        ecole=personnel.ecole, enserignant=personnel
    ).values_list('section_id', flat=True)
    return (
        Classe.objects.filter(ecole=personnel.ecole)
        .filter(
            Q(titulaire=personnel)
            | Q(id__in=aff_classes)
            | Q(section_id__in=sections_matieres)
        )
        .distinct()
        .order_by('classe')
    )


def _matieres_enseignant(personnel):
    sections_classes = Classe.objects.filter(
        ecole=personnel.ecole, titulaire=personnel
    ).values_list('section_id', flat=True)
    aff_matieres = AffectationEnseignement.objects.filter(
        enseignant=personnel, ecole=personnel.ecole
    ).values_list('matiere_id', flat=True)
    return (
        Matiere.objects.filter(ecole=personnel.ecole)
        .filter(
            Q(enserignant=personnel)
            | Q(section_id__in=sections_classes)
            | Q(id__in=aff_matieres)
        )
        .distinct()
        .order_by('libelle')
    )


def _peut_acceder_travail(personnel, travail):
    if travail.ecole_id != personnel.ecole_id:
        return False
    return peut_gerer_matiere_classe(personnel, travail.matiere, travail.classe)


@login_required
def travail_list(request):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    travaux = _travaux_qs(personnel).order_by('-date_travail', '-id')

    classe_id = request.GET.get('classe')
    matiere_id = request.GET.get('matiere')
    type_travail = request.GET.get('type')

    if classe_id:
        travaux = travaux.filter(classe_id=classe_id)
    if matiere_id:
        travaux = travaux.filter(matiere_id=matiere_id)
    if type_travail:
        travaux = travaux.filter(type_travail=type_travail)

    travaux = list(travaux)
    for t in travaux:
        t.nb_attendus = t.nb_eleves_attendus
        t.nb_saisies = t.nb_notes_saisies

    return render(request, 'utilisateur/travail_list.html', {
        'travaux': travaux,
        'classes': _classes_enseignant(personnel),
        'matieres': _matieres_enseignant(personnel),
        'type_choices': TravailCote.TYPE_CHOICES,
        'filtre_classe': classe_id or '',
        'filtre_matiere': matiere_id or '',
        'filtre_type': type_travail or '',
        'total_travaux': len(travaux),
        'total_notes_manquantes': sum(1 for t in travaux if not t.est_complet),
    })


@login_required
def travail_create(request):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    ecole = personnel.ecole
    classes_qs = _classes_enseignant(personnel)
    matieres_qs = _matieres_enseignant(personnel)

    if request.method == 'POST':
        form = TravailCoteForm(
            request.POST, ecole=ecole, classes_qs=classes_qs, matieres_qs=matieres_qs
        )
        if form.is_valid():
            travail = form.save(commit=False)
            travail.ecole = ecole
            if not _peut_acceder_travail(personnel, travail):
                messages.error(request, "Vous ne pouvez pas créer un travail pour cette classe / matière.")
            else:
                travail.save()
                messages.success(request, "Le travail coté a été enregistré.")
                return redirect('utilisateur:travail_notes', pk=travail.pk)
    else:
        annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
        initial = {'annee_scolaire': annee}
        if request.GET.get('classe'):
            initial['classe'] = request.GET.get('classe')
        form = TravailCoteForm(
            ecole=ecole, classes_qs=classes_qs, matieres_qs=matieres_qs, initial=initial
        )

    return render(request, 'utilisateur/travail_form.html', {
        'form': form,
        'title': 'Nouveau travail coté',
        'matieres_count': matieres_qs.count(),
        'classes_count': classes_qs.count(),
    })


@login_required
def travail_update(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    travail = get_object_or_404(TravailCote, pk=pk, ecole=personnel.ecole)
    if not _peut_acceder_travail(personnel, travail):
        messages.error(request, "Accès non autorisé à ce travail.")
        return redirect('utilisateur:travail_list')

    classes_qs = _classes_enseignant(personnel)
    matieres_qs = _matieres_enseignant(personnel)

    if request.method == 'POST':
        form = TravailCoteForm(
            request.POST, instance=travail, ecole=personnel.ecole,
            classes_qs=classes_qs, matieres_qs=matieres_qs,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Le travail coté a été modifié.")
            return redirect('utilisateur:travail_list')
    else:
        form = TravailCoteForm(
            instance=travail, ecole=personnel.ecole,
            classes_qs=classes_qs, matieres_qs=matieres_qs,
        )

    return render(request, 'utilisateur/travail_form.html', {
        'form': form,
        'travail': travail,
        'title': 'Modifier le travail coté',
    })


@login_required
def travail_delete(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    travail = get_object_or_404(TravailCote, pk=pk, ecole=personnel.ecole)
    if not _peut_acceder_travail(personnel, travail):
        messages.error(request, "Accès non autorisé à ce travail.")
        return redirect('utilisateur:travail_list')

    if request.method == 'POST':
        travail.delete()
        messages.success(request, "Le travail coté a été supprimé.")
        return redirect('utilisateur:travail_list')

    return render(request, 'utilisateur/travail_confirm_delete.html', {'travail': travail})


@login_required
def travail_notes(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    travail = get_object_or_404(
        TravailCote.objects.select_related('matiere', 'classe', 'annee_scolaire'),
        pk=pk,
        ecole=personnel.ecole,
    )
    if not _peut_acceder_travail(personnel, travail):
        messages.error(request, "Accès non autorisé à ce travail.")
        return redirect('utilisateur:travail_list')

    inscriptions = (
        Inscription.objects.filter(classe=travail.classe, annee_s=travail.annee_scolaire)
        .select_related('eleve')
        .order_by('eleve__nom', 'eleve__prenom')
    )
    notes_existantes = {n.inscription_id: n for n in travail.notes.all()}

    if request.method == 'POST':
        erreurs = False
        saisies = 0
        ignorees = 0
        with suspendre_actualisation_bulletins():
            for ins in inscriptions:
                existante = notes_existantes.get(ins.id)
                if existante and existante.est_verrouillee:
                    ignorees += 1
                    continue

                absent = request.POST.get(f'absent_{ins.id}') == 'on'
                note_raw = (request.POST.get(f'note_{ins.id}') or '').strip()
                note_value = None
                if note_raw and not absent:
                    try:
                        note_value = Decimal(note_raw.replace(',', '.'))
                    except InvalidOperation:
                        messages.error(request, f"Note invalide pour {ins.eleve}.")
                        erreurs = True
                        continue
                    if note_value < 0 or note_value > travail.bareme:
                        messages.error(
                            request,
                            f"La note de {ins.eleve} doit être comprise entre 0 et {travail.bareme}.",
                        )
                        erreurs = True
                        continue

                # Ne rien enregistrer tant qu'aucune note / absence n'est saisie
                if note_value is None and not absent:
                    continue

                NoteEleve.objects.update_or_create(
                    travail=travail,
                    inscription=ins,
                    defaults={'note': note_value, 'absent': absent},
                )
                saisies += 1

        actualiser_bulletins_inscriptions(inscriptions)

        if not erreurs:
            if saisies:
                messages.success(
                    request,
                    f"{saisies} note(s) enregistrée(s) et verrouillée(s). Bulletins mis à jour.",
                )
            elif ignorees:
                messages.warning(
                    request,
                    "Toutes les notes déjà saisies sont verrouillées et ne peuvent plus être modifiées.",
                )
            else:
                messages.info(request, "Aucune nouvelle note à enregistrer.")
            return redirect('utilisateur:travail_notes', pk=travail.pk)
        notes_existantes = {n.inscription_id: n for n in travail.notes.all()}

    rows = []
    for ins in inscriptions:
        note_obj = notes_existantes.get(ins.id)
        verrouillee = bool(note_obj and note_obj.est_verrouillee)
        rows.append({
            'inscription': ins,
            'note': note_obj.note if note_obj else None,
            'absent': note_obj.absent if note_obj else False,
            'verrouillee': verrouillee,
        })

    nb_verrouillees = sum(1 for r in rows if r['verrouillee'])
    return render(request, 'utilisateur/travail_notes.html', {
        'travail': travail,
        'rows': rows,
        'nb_attendus': len(rows),
        'nb_saisies': nb_verrouillees,
        'nb_verrouillees': nb_verrouillees,
        'peut_saisir': any(not r['verrouillee'] for r in rows),
    })
