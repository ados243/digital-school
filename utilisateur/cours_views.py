"""Cours en ligne — espace enseignant (publier) et élève (étudier)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from inscription.models import Annee_Scolaire
from pedagogie.affectations import peut_gerer_matiere_classe
from pedagogie.forms import ChapitreCoursForm, CoursEnLigneForm, LeconEnLigneForm
from pedagogie.models import ChapitreCours, CoursEnLigne, LeconEnLigne, Matiere, ProgressionLecon
from utilisateur.travaux_views import (
    _classes_enseignant,
    _matieres_enseignant,
    _require_enseignant,
)


# ─── Enseignant ──────────────────────────────────────────────────────────────


def _cours_enseignant_qs(personnel):
    """Cours que l'enseignant peut gérer (auteur ou droit classe/matière)."""
    base = (
        CoursEnLigne.objects.filter(ecole=personnel.ecole)
        .select_related('classe', 'matiere', 'enseignant', 'annee_scolaire')
        .annotate(
            lecons_total=Count('lecons', distinct=True),
            lecons_pub=Count(
                'lecons',
                filter=Q(lecons__publie=True, lecons__chapitre__publie=True),
                distinct=True,
            ),
            chapitres_total=Count('chapitres', distinct=True),
        )
    )
    ids = [
        c.id for c in base
        if c.enseignant_id == personnel.id
        or peut_gerer_matiere_classe(personnel, c.matiere, c.classe)
    ]
    return base.filter(id__in=ids).order_by('-updated_at')


def _peut_gerer_cours(personnel, cours):
    if cours.ecole_id != personnel.ecole_id:
        return False
    if cours.enseignant_id == personnel.id:
        return True
    return peut_gerer_matiere_classe(personnel, cours.matiere, cours.classe)


@login_required
def cours_enseignant_list(request):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    cours_list = list(_cours_enseignant_qs(personnel))
    classe_id = request.GET.get('classe')
    matiere_id = request.GET.get('matiere')
    statut = request.GET.get('statut')

    if classe_id:
        cours_list = [c for c in cours_list if str(c.classe_id) == classe_id]
    if matiere_id:
        cours_list = [c for c in cours_list if str(c.matiere_id) == matiere_id]
    if statut == 'publie':
        cours_list = [c for c in cours_list if c.publie]
    elif statut == 'brouillon':
        cours_list = [c for c in cours_list if not c.publie]

    return render(request, 'utilisateur/cours_enseignant_list.html', {
        'cours_list': cours_list,
        'classes': _classes_enseignant(personnel),
        'matieres': _matieres_enseignant(personnel),
        'filtre_classe': classe_id or '',
        'filtre_matiere': matiere_id or '',
        'filtre_statut': statut or '',
        'nb_publies': sum(1 for c in cours_list if c.publie),
        'nb_brouillons': sum(1 for c in cours_list if not c.publie),
    })


@login_required
def cours_enseignant_create(request):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    ecole = personnel.ecole
    classes_qs = _classes_enseignant(personnel)
    matieres_qs = _matieres_enseignant(personnel)

    if request.method == 'POST':
        form = CoursEnLigneForm(
            request.POST, request.FILES, ecole=ecole, classes_qs=classes_qs, matieres_qs=matieres_qs
        )
        if form.is_valid():
            cours = form.save(commit=False)
            cours.ecole = ecole
            cours.enseignant = personnel
            if not peut_gerer_matiere_classe(personnel, cours.matiere, cours.classe):
                messages.error(request, "Vous ne pouvez pas créer un cours pour cette classe / matière.")
            else:
                cours.save()
                messages.success(request, "Cours créé. Ajoutez des chapitres, puis publiez-le.")
                return redirect('utilisateur:cours_enseignant_detail', pk=cours.pk)
    else:
        annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
        initial = {'annee_scolaire': annee}
        if request.GET.get('classe'):
            initial['classe'] = request.GET.get('classe')
        if request.GET.get('matiere'):
            initial['matiere'] = request.GET.get('matiere')
        form = CoursEnLigneForm(
            ecole=ecole, classes_qs=classes_qs, matieres_qs=matieres_qs, initial=initial
        )

    return render(request, 'utilisateur/cours_enseignant_form.html', {
        'form': form,
        'title': 'Nouveau cours en ligne',
    })


@login_required
def cours_enseignant_update(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    cours = get_object_or_404(CoursEnLigne, pk=pk, ecole=personnel.ecole)
    if not _peut_gerer_cours(personnel, cours):
        messages.error(request, "Accès non autorisé à ce cours.")
        return redirect('utilisateur:cours_enseignant_list')

    classes_qs = _classes_enseignant(personnel)
    matieres_qs = _matieres_enseignant(personnel)

    if request.method == 'POST':
        form = CoursEnLigneForm(
            request.POST, request.FILES, instance=cours, ecole=personnel.ecole,
            classes_qs=classes_qs, matieres_qs=matieres_qs,
        )
        if form.is_valid():
            updated = form.save(commit=False)
            if not peut_gerer_matiere_classe(personnel, updated.matiere, updated.classe):
                messages.error(request, "Classe / matière non autorisée.")
            else:
                updated.save()
                messages.success(request, "Cours mis à jour.")
                return redirect('utilisateur:cours_enseignant_detail', pk=cours.pk)
    else:
        form = CoursEnLigneForm(
            instance=cours, ecole=personnel.ecole,
            classes_qs=classes_qs, matieres_qs=matieres_qs,
        )

    return render(request, 'utilisateur/cours_enseignant_form.html', {
        'form': form,
        'cours': cours,
        'title': 'Modifier le cours',
    })


@login_required
def cours_enseignant_detail(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    cours = get_object_or_404(
        CoursEnLigne.objects.select_related('classe', 'matiere', 'enseignant', 'annee_scolaire'),
        pk=pk,
        ecole=personnel.ecole,
    )
    if not _peut_gerer_cours(personnel, cours):
        messages.error(request, "Accès non autorisé à ce cours.")
        return redirect('utilisateur:cours_enseignant_list')

    chapitre_form = ChapitreCoursForm(initial={'ordre': cours.chapitres.count() + 1})

    if request.method == 'POST' and request.POST.get('action') == 'ajouter_chapitre':
        chapitre_form = ChapitreCoursForm(request.POST, request.FILES)
        if chapitre_form.is_valid():
            chapitre = chapitre_form.save(commit=False)
            chapitre.cours = cours
            chapitre.save()
            messages.success(request, f"Chapitre « {chapitre.titre} » ajouté.")
            return redirect('utilisateur:chapitre_enseignant_detail', pk=chapitre.pk)

    structure = cours.structure_pedagogique(publie_only=False)

    return render(request, 'utilisateur/cours_enseignant_detail.html', {
        'cours': cours,
        'structure': structure,
        'chapitre_form': chapitre_form,
        'nb_sous': sum(len(sous) for _, sous in structure),
    })


@login_required
def chapitre_enseignant_detail(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    chapitre = get_object_or_404(
        ChapitreCours.objects.select_related(
            'cours', 'cours__classe', 'cours__matiere', 'cours__ecole'
        ),
        pk=pk,
        cours__ecole=personnel.ecole,
    )
    if not _peut_gerer_cours(personnel, chapitre.cours):
        messages.error(request, "Accès non autorisé.")
        return redirect('utilisateur:cours_enseignant_list')

    sous_chapitres = chapitre.sous_chapitres.all()
    sous_form = LeconEnLigneForm(initial={'ordre': sous_chapitres.count() + 1})

    if request.method == 'POST' and request.POST.get('action') == 'ajouter_sous':
        sous_form = LeconEnLigneForm(request.POST, request.FILES)
        if sous_form.is_valid():
            lecon = sous_form.save(commit=False)
            lecon.chapitre = chapitre
            lecon.cours = chapitre.cours
            lecon.save()
            messages.success(request, f"Sous-chapitre « {lecon.titre} » ajouté.")
            return redirect('utilisateur:chapitre_enseignant_detail', pk=chapitre.pk)

    return render(request, 'utilisateur/chapitre_enseignant_detail.html', {
        'cours': chapitre.cours,
        'chapitre': chapitre,
        'sous_chapitres': sous_chapitres,
        'sous_form': sous_form,
    })


@login_required
def chapitre_enseignant_update(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    chapitre = get_object_or_404(
        ChapitreCours.objects.select_related('cours'),
        pk=pk,
        cours__ecole=personnel.ecole,
    )
    if not _peut_gerer_cours(personnel, chapitre.cours):
        messages.error(request, "Accès non autorisé.")
        return redirect('utilisateur:cours_enseignant_list')

    if request.method == 'POST':
        form = ChapitreCoursForm(request.POST, request.FILES, instance=chapitre)
        if form.is_valid():
            form.save()
            messages.success(request, "Chapitre mis à jour.")
            return redirect('utilisateur:chapitre_enseignant_detail', pk=chapitre.pk)
    else:
        form = ChapitreCoursForm(instance=chapitre)

    return render(request, 'utilisateur/chapitre_enseignant_form.html', {
        'form': form,
        'cours': chapitre.cours,
        'chapitre': chapitre,
        'title': 'Modifier le chapitre',
    })


@login_required
def chapitre_enseignant_delete(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    chapitre = get_object_or_404(
        ChapitreCours.objects.select_related('cours'),
        pk=pk,
        cours__ecole=personnel.ecole,
    )
    if not _peut_gerer_cours(personnel, chapitre.cours):
        messages.error(request, "Accès non autorisé.")
        return redirect('utilisateur:cours_enseignant_list')

    cours_id = chapitre.cours_id
    if request.method == 'POST':
        titre = chapitre.titre
        chapitre.delete()
        messages.success(request, f"Chapitre « {titre} » supprimé.")
        return redirect('utilisateur:cours_enseignant_detail', pk=cours_id)

    return render(request, 'utilisateur/chapitre_enseignant_confirm_delete.html', {
        'chapitre': chapitre,
        'cours': chapitre.cours,
    })


@login_required
def cours_enseignant_publier(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    cours = get_object_or_404(CoursEnLigne, pk=pk, ecole=personnel.ecole)
    if not _peut_gerer_cours(personnel, cours):
        messages.error(request, "Accès non autorisé.")
        return redirect('utilisateur:cours_enseignant_list')

    if request.method == 'POST':
        action = request.POST.get('action', 'publier')
        if action == 'depublier':
            cours.publie = False
            cours.save(update_fields=['publie', 'updated_at'])
            messages.info(request, "Cours retiré de la publication (brouillon).")
        else:
            has_content = LeconEnLigne.objects.filter(
                cours=cours, publie=True, chapitre__publie=True
            ).exists()
            if not has_content:
                messages.warning(
                    request,
                    "Ajoutez au moins un sous-chapitre visible dans un chapitre avant de publier.",
                )
                return redirect('utilisateur:cours_enseignant_detail', pk=cours.pk)
            cours.publie = True
            cours.date_publication = timezone.now()
            cours.save(update_fields=['publie', 'date_publication', 'updated_at'])
            messages.success(
                request,
                f"Cours publié : les élèves de {cours.classe.classe} peuvent l'étudier en ligne.",
            )
    return redirect('utilisateur:cours_enseignant_detail', pk=cours.pk)


@login_required
def cours_enseignant_delete(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    cours = get_object_or_404(CoursEnLigne, pk=pk, ecole=personnel.ecole)
    if not _peut_gerer_cours(personnel, cours):
        messages.error(request, "Accès non autorisé.")
        return redirect('utilisateur:cours_enseignant_list')

    if request.method == 'POST':
        titre = cours.titre
        cours.delete()
        messages.success(request, f"Cours « {titre} » supprimé.")
        return redirect('utilisateur:cours_enseignant_list')

    return render(request, 'utilisateur/cours_enseignant_confirm_delete.html', {'cours': cours})


@login_required
def lecon_enseignant_update(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    lecon = get_object_or_404(
        LeconEnLigne.objects.select_related(
            'cours', 'chapitre', 'cours__classe', 'cours__matiere'
        ),
        pk=pk,
        cours__ecole=personnel.ecole,
    )
    if not _peut_gerer_cours(personnel, lecon.cours):
        messages.error(request, "Accès non autorisé.")
        return redirect('utilisateur:cours_enseignant_list')

    if request.method == 'POST':
        form = LeconEnLigneForm(request.POST, request.FILES, instance=lecon)
        if form.is_valid():
            form.save()
            messages.success(request, "Sous-chapitre mis à jour.")
            if lecon.chapitre_id:
                return redirect('utilisateur:chapitre_enseignant_detail', pk=lecon.chapitre_id)
            return redirect('utilisateur:cours_enseignant_detail', pk=lecon.cours_id)
    else:
        form = LeconEnLigneForm(instance=lecon)

    return render(request, 'utilisateur/lecon_enseignant_form.html', {
        'form': form,
        'lecon': lecon,
        'cours': lecon.cours,
        'chapitre': lecon.chapitre,
        'title': 'Modifier le sous-chapitre',
    })


@login_required
def lecon_enseignant_delete(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    lecon = get_object_or_404(
        LeconEnLigne.objects.select_related('cours', 'chapitre'),
        pk=pk,
        cours__ecole=personnel.ecole,
    )
    if not _peut_gerer_cours(personnel, lecon.cours):
        messages.error(request, "Accès non autorisé.")
        return redirect('utilisateur:cours_enseignant_list')

    chapitre_id = lecon.chapitre_id
    cours_id = lecon.cours_id
    if request.method == 'POST':
        lecon.delete()
        messages.success(request, "Sous-chapitre supprimé.")
        if chapitre_id:
            return redirect('utilisateur:chapitre_enseignant_detail', pk=chapitre_id)
        return redirect('utilisateur:cours_enseignant_detail', pk=cours_id)

    return render(request, 'utilisateur/lecon_enseignant_confirm_delete.html', {
        'lecon': lecon,
        'cours': lecon.cours,
        'chapitre': lecon.chapitre,
    })


# ─── Élève ───────────────────────────────────────────────────────────────────


def _require_eleve(request):
    if not request.user.is_eleve:
        return None, None, redirect('utilisateur:post_login')
    eleve = request.user.eleve
    if not eleve:
        messages.warning(request, "Aucune fiche élève n'est rattachée à votre compte.")
        return None, None, redirect('utilisateur:portail')
    from utilisateur.views import _inscription_courante
    inscription = _inscription_courante(eleve)
    if not inscription:
        messages.warning(request, "Aucune inscription active pour étudier en ligne.")
        return None, None, redirect('utilisateur:portail')
    return eleve, inscription, None


def _cours_publies_eleve(inscription):
    return (
        CoursEnLigne.objects.filter(
            publie=True,
            ecole=inscription.eleve.ecole,
            classe=inscription.classe,
            annee_scolaire=inscription.annee_s,
        )
        .select_related('matiere', 'enseignant', 'classe')
        .annotate(
            lecons_pub=Count(
                'lecons',
                filter=Q(lecons__publie=True, lecons__chapitre__publie=True),
                distinct=True,
            )
        )
        .order_by('matiere__libelle', 'titre')
    )


def _build_progress_structure(cours, inscription):
    structure = cours.structure_pedagogique(publie_only=True)
    lecons = [sc for _, sous in structure for sc in sous]
    progress_map = {
        p.lecon_id: p
        for p in ProgressionLecon.objects.filter(inscription=inscription, lecon__in=lecons)
    }
    chapters_rows = []
    lecons_rows = []
    for chapitre, sous in structure:
        sous_rows = []
        for sc in sous:
            prog = progress_map.get(sc.id)
            row = {
                'lecon': sc,
                'vue': bool(prog and prog.vue),
                'terminee': bool(prog and prog.terminee),
            }
            sous_rows.append(row)
            lecons_rows.append({**row, 'chapitre': chapitre})
        chapters_rows.append({
            'chapitre': chapitre,
            'sous_rows': sous_rows,
            'terminees': sum(1 for r in sous_rows if r['terminee']),
            'total': len(sous_rows),
        })
    return chapters_rows, lecons_rows, lecons


@login_required
def cours_eleve_list(request):
    eleve, inscription, err = _require_eleve(request)
    if err:
        return err

    cours_qs = _cours_publies_eleve(inscription)
    matiere_id = request.GET.get('matiere')
    niveau = request.GET.get('niveau')
    q = (request.GET.get('q') or '').strip()

    if matiere_id:
        cours_qs = cours_qs.filter(matiere_id=matiere_id)
    if niveau:
        cours_qs = cours_qs.filter(niveau=niveau)
    if q:
        cours_qs = cours_qs.filter(
            Q(titre__icontains=q)
            | Q(sous_titre__icontains=q)
            | Q(description__icontains=q)
            | Q(competences__icontains=q)
            | Q(matiere__libelle__icontains=q)
        )

    tous_cours = list(cours_qs)
    par_matiere = {}
    for c in tous_cours:
        par_matiere.setdefault(c.matiere, []).append(c)

    matieres = (
        Matiere.objects.filter(
            ecole=eleve.ecole,
            section=inscription.classe.section,
            cours_en_ligne__publie=True,
            cours_en_ligne__classe=inscription.classe,
            cours_en_ligne__annee_scolaire=inscription.annee_s,
        )
        .distinct()
        .order_by('libelle')
    )

    return render(request, 'utilisateur/cours_eleve_list.html', {
        'inscription': inscription,
        'par_matiere': list(par_matiere.items()),
        'matieres': matieres,
        'filtre_matiere': matiere_id or '',
        'filtre_niveau': niveau or '',
        'filtre_q': q,
        'total_cours': len(tous_cours),
        'niveaux': CoursEnLigne.NIVEAU_CHOICES,
        'cours_recents': tous_cours[:6],
    })


@login_required
def cours_eleve_detail(request, pk):
    eleve, inscription, err = _require_eleve(request)
    if err:
        return err

    cours = get_object_or_404(
        CoursEnLigne.objects.select_related('matiere', 'enseignant', 'classe'),
        pk=pk,
        publie=True,
        ecole=eleve.ecole,
        classe=inscription.classe,
    )
    chapters_rows, lecons_rows, lecons = _build_progress_structure(cours, inscription)
    terminees = sum(1 for r in lecons_rows if r['terminee'])
    total = len(lecons) or 1
    progression_pct = int(round(100 * terminees / total)) if lecons else 0
    premiere = lecons[0] if lecons else None
    prochaine = next((r['lecon'] for r in lecons_rows if not r['terminee']), premiere)

    return render(request, 'utilisateur/cours_eleve_detail.html', {
        'inscription': inscription,
        'cours': cours,
        'chapters_rows': chapters_rows,
        'lecons': lecons,
        'lecons_rows': lecons_rows,
        'terminees': terminees,
        'progression_pct': progression_pct,
        'premiere_lecon': premiere,
        'prochaine_lecon': prochaine,
        'nb_chapitres': len(chapters_rows),
    })


@login_required
def chapitre_eleve_detail(request, pk):
    eleve, inscription, err = _require_eleve(request)
    if err:
        return err

    chapitre = get_object_or_404(
        ChapitreCours.objects.select_related(
            'cours', 'cours__matiere', 'cours__enseignant', 'cours__classe'
        ),
        pk=pk,
        publie=True,
        cours__publie=True,
        cours__ecole=eleve.ecole,
        cours__classe=inscription.classe,
    )
    cours = chapitre.cours
    chapters_rows, lecons_rows, lecons = _build_progress_structure(cours, inscription)
    sous = [r for r in lecons_rows if r['chapitre'].id == chapitre.id]
    premiere = sous[0]['lecon'] if sous else None

    return render(request, 'utilisateur/chapitre_eleve_detail.html', {
        'inscription': inscription,
        'cours': cours,
        'chapitre': chapitre,
        'sous_rows': sous,
        'premiere_sous': premiere,
        'chapters_rows': chapters_rows,
    })


@login_required
def lecon_eleve_detail(request, pk):
    eleve, inscription, err = _require_eleve(request)
    if err:
        return err

    lecon = get_object_or_404(
        LeconEnLigne.objects.select_related(
            'cours', 'chapitre', 'cours__matiere', 'cours__enseignant', 'cours__classe'
        ),
        pk=pk,
        publie=True,
        chapitre__publie=True,
        cours__publie=True,
        cours__ecole=eleve.ecole,
        cours__classe=inscription.classe,
    )
    cours = lecon.cours
    chapters_rows, lecons_rows, lecons = _build_progress_structure(cours, inscription)
    idx = next((i for i, l in enumerate(lecons) if l.id == lecon.id), 0)
    prev_lecon = lecons[idx - 1] if idx > 0 else None
    next_lecon = lecons[idx + 1] if idx + 1 < len(lecons) else None

    progression, _ = ProgressionLecon.objects.get_or_create(
        inscription=inscription, lecon=lecon, defaults={'vue': True}
    )
    if not progression.vue:
        progression.vue = True
        progression.save(update_fields=['vue'])

    if request.method == 'POST' and request.POST.get('action') == 'terminer':
        progression.terminee = True
        progression.terminee_at = timezone.now()
        progression.save(update_fields=['terminee', 'terminee_at'])
        messages.success(request, "Sous-chapitre marqué comme terminé.")
        if next_lecon:
            return redirect('utilisateur:lecon_eleve_detail', pk=next_lecon.pk)
        return redirect('utilisateur:cours_eleve_detail', pk=cours.pk)

    for row in lecons_rows:
        row['courante'] = row['lecon'].id == lecon.id

    terminees = sum(1 for r in lecons_rows if r['terminee'])
    progression_pct = int(round(100 * terminees / (len(lecons) or 1))) if lecons else 0

    return render(request, 'utilisateur/lecon_eleve_detail.html', {
        'inscription': inscription,
        'cours': cours,
        'chapitre': lecon.chapitre,
        'lecon': lecon,
        'lecons': lecons,
        'lecons_rows': lecons_rows,
        'chapters_rows': chapters_rows,
        'prev_lecon': prev_lecon,
        'next_lecon': next_lecon,
        'lecon_index': idx + 1,
        'lecons_total': len(lecons),
        'progression': progression,
        'progression_pct': progression_pct,
    })
