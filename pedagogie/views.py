from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.urls import reverse
from django.views.decorators.http import require_POST
from datetime import date, datetime
from collections import defaultdict

from .models import Matiere, PresenceClasse, PresenceEleve, DivisionAnnee, PeriodeBulletin
from .forms import MatiereForm
from .periodes_utils import (
    desactiver_periodes_expirees,
    marquer_division_encours,
    marquer_periode_encours,
    resume_encours,
    synchroniser_encours,
)
from inscription.models import Classe, Section, Annee_Scolaire, Inscription, Cycle
from common.tenant import get_user_ecole


def _peut_editer_calendrier_national(user):
    """Le calendrier MINEDU est partagé : seuls manager / superuser le basculent."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return getattr(user, "role", None) == "MANAGER"


@login_required
def pedagogie_dashboard(request):
    ecole = get_user_ecole(request)
    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    calendrier_encours = resume_encours(annee=annee)

    matieres = Matiere.objects.filter(ecole=ecole).select_related('section').order_by('section__section', 'libelle')
    classes = Classe.objects.filter(ecole=ecole).select_related('section').order_by('section__section', 'classe')

    inscrits_par_classe = {}
    if annee:
        for row in (
            Inscription.objects.filter(classe__ecole=ecole, annee_s=annee)
            .values('classe_id')
            .annotate(total=Count('id'))
        ):
            inscrits_par_classe[row['classe_id']] = row['total']

    matieres_par_section = defaultdict(list)
    for m in matieres:
        matieres_par_section[m.section_id].append(m)
    classes_par_section = defaultdict(list)
    for c in classes:
        classes_par_section[c.section_id].append(c)

    section_ids = set(matieres_par_section) | set(classes_par_section)
    sections = (
        Section.objects.filter(pk__in=section_ids).select_related('cycle').order_by('cycle__cycle', 'section')
        if section_ids
        else Section.objects.none()
    )

    sections_data = {}
    total_inscrits = 0
    classes_completes = 0

    for s in sections:
        sec_matieres = matieres_par_section.get(s.id, [])
        sec_classes = classes_par_section.get(s.id, [])
        total_coef = sum((m.coefficient or 0) for m in sec_matieres)
        classes_detail = []
        for c in sec_classes:
            inscrits = inscrits_par_classe.get(c.id, 0)
            total_inscrits += inscrits
            is_full = inscrits >= c.capacite_max
            if is_full:
                classes_completes += 1
            percent = int((inscrits / c.capacite_max) * 100) if c.capacite_max > 0 else 0
            classes_detail.append({
                'obj': c,
                'inscrits': inscrits,
                'percent': percent,
                'is_full': is_full,
            })
        sections_data[s] = {
            'matieres': sec_matieres,
            'classes': classes_detail,
            'total_coefficient': total_coef,
            'matieres_count': len(sec_matieres),
            'classes_count': len(sec_classes),
        }

    stats = {
        'total_matieres': matieres.count(),
        'total_classes': classes.count(),
        'total_sections': len(sections_data),
        'total_inscrits': total_inscrits,
        'classes_completes': classes_completes,
        'annee_courante': annee,
    }

    context = {
        'sections_data': sections_data,
        'stats': stats,
        'matieres': matieres,
        'classes': classes,
        'calendrier_encours': calendrier_encours,
    }
    return render(request, 'pedagogie/dashboard.html', context)


@login_required
def periodes_bulletin(request):
    """Repartition de l'annee scolaire selon le bulletin RDC (par cycle/section)."""
    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    if not annee:
        annee = Annee_Scolaire.objects.order_by('-date_debut').first()

    desactiver_periodes_expirees()

    if request.method == 'POST' and request.POST.get('action') == 'sync':
        if not _peut_editer_calendrier_national(request.user):
            messages.error(
                request,
                "Seul un administrateur plateforme peut synchroniser le calendrier national.",
            )
            return redirect('pedagogie:periodes_bulletin')
        synchroniser_encours(annee=annee)
        messages.success(
            request,
            "Statut « en cours » synchronisé selon la date du jour "
            "(les périodes expirées sont désactivées).",
        )
        return redirect('pedagogie:periodes_bulletin')

    cycles_data = []
    if annee:
        sections_par_cycle = {}
        for s in Section.objects.select_related('cycle').order_by('section'):
            sections_par_cycle.setdefault(s.cycle_id, []).append(s.section)

        for cycle in Cycle.objects.order_by('id'):
            divisions = (
                DivisionAnnee.objects.filter(annee_scolaire=annee, cycle=cycle)
                .prefetch_related('periodes')
                .order_by('numero')
            )
            if not divisions.exists():
                continue
            mode = divisions.first().get_type_division_display()
            cycles_data.append({
                'cycle': cycle,
                'mode': mode,
                'sections': sections_par_cycle.get(cycle.id, []),
                'divisions': [
                    {
                        'obj': d,
                        'periodes': list(d.periodes.all()),
                    }
                    for d in divisions
                ],
                'nb_periodes': PeriodeBulletin.objects.filter(
                    annee_scolaire=annee, cycle=cycle
                ).count(),
            })

    return render(request, 'pedagogie/periodes_bulletin.html', {
        'annee_courante': annee,
        'cycles_data': cycles_data,
        'aujourdhui': date.today(),
        'calendrier_encours': resume_encours(annee=annee),
        'peut_editer_calendrier': _peut_editer_calendrier_national(request.user),
    })


@login_required
@require_POST
def division_toggle_encours(request, pk):
    if not _peut_editer_calendrier_national(request.user):
        messages.error(
            request,
            "Le calendrier bulletin est national : seuls le manager et le superutilisateur peuvent le modifier.",
        )
        return redirect(request.POST.get('next') or 'pedagogie:periodes_bulletin')
    division = get_object_or_404(DivisionAnnee.objects.select_related('cycle'), pk=pk)
    desactiver_periodes_expirees()
    if division.est_encours:
        division.est_encours = False
        division.save(update_fields=['est_encours'])
        messages.info(
            request,
            f'« {division.libelle} » n\'est plus marqué en cours.',
        )
    else:
        ok = marquer_division_encours(division)
        if ok:
            messages.success(
                request,
                f'« {division.libelle} » ({division.cycle.cycle}) est maintenant en cours.',
            )
        else:
            messages.error(
                request,
                f'Impossible : {division.libelle} est déjà terminé '
                f'(fin le {division.date_fin.strftime("%d/%m/%Y")}).',
            )
    return redirect(request.POST.get('next') or 'pedagogie:periodes_bulletin')


@login_required
@require_POST
def periode_toggle_encours(request, pk):
    if not _peut_editer_calendrier_national(request.user):
        messages.error(
            request,
            "Le calendrier bulletin est national : seuls le manager et le superutilisateur peuvent le modifier.",
        )
        return redirect(request.POST.get('next') or 'pedagogie:periodes_bulletin')
    periode = get_object_or_404(
        PeriodeBulletin.objects.select_related('cycle', 'division'), pk=pk
    )
    desactiver_periodes_expirees()
    if periode.est_encours:
        periode.est_encours = False
        periode.save(update_fields=['est_encours'])
        messages.info(
            request,
            f'« {periode.libelle} » n\'est plus marquée en cours.',
        )
    else:
        ok = marquer_periode_encours(periode)
        if ok:
            messages.success(
                request,
                f'« {periode.libelle} » ({periode.cycle.cycle}) est maintenant en cours.',
            )
        else:
            messages.error(
                request,
                f'Impossible : {periode.libelle} est déjà terminée '
                f'(fin le {periode.date_fin.strftime("%d/%m/%Y")}).',
            )
    return redirect(request.POST.get('next') or 'pedagogie:periodes_bulletin')


@login_required
def matiere_list(request):
    """Liste de toutes les matières de l'école."""
    ecole = request.user.ecole
    matieres = (
        Matiere.objects.filter(ecole=ecole)
        .select_related('section', 'section__cycle', 'enserignant')
        .order_by('section__section', 'libelle')
    )
    section_id = request.GET.get('section')
    if section_id:
        matieres = matieres.filter(section_id=section_id)

    total_coef = matieres.aggregate(total=Sum('coefficient'))['total'] or 0
    sections = Section.objects.filter(
        id__in=Matiere.objects.filter(ecole=ecole).values_list('section_id', flat=True)
    ).order_by('section')

    return render(request, 'pedagogie/matiere_list.html', {
        'matieres': matieres,
        'sections': sections,
        'filtre_section': section_id or '',
        'total_matieres': matieres.count(),
        'total_coefficient': total_coef,
    })


@login_required
def matiere_create(request):
    ecole = request.user.ecole
    if request.method == 'POST':
        form = MatiereForm(request.POST, ecole=ecole)
        if form.is_valid():
            matiere = form.save(commit=False)
            matiere.ecole = ecole
            matiere.save()
            messages.success(request, f"La matière '{matiere.libelle}' a été créée avec succès.")
            return redirect('pedagogie:matiere_list')
    else:
        form = MatiereForm(ecole=ecole)

    return render(request, 'pedagogie/matiere_form.html', {'form': form, 'title': 'Nouvelle Matière'})


@login_required
def matiere_update(request, pk):
    ecole = request.user.ecole
    matiere = get_object_or_404(Matiere, pk=pk, ecole=ecole)
    if request.method == 'POST':
        form = MatiereForm(request.POST, instance=matiere, ecole=ecole)
        if form.is_valid():
            form.save()
            messages.success(request, f"La matière '{matiere.libelle}' a été modifiée.")
            return redirect('pedagogie:matiere_list')
    else:
        form = MatiereForm(instance=matiere, ecole=ecole)

    return render(request, 'pedagogie/matiere_form.html', {'form': form, 'matiere': matiere, 'title': 'Modifier la Matière'})

@login_required
def matiere_delete(request, pk):
    matiere = get_object_or_404(Matiere, pk=pk, ecole=request.user.ecole)
    if request.method == 'POST':
        libelle = matiere.libelle
        matiere.delete()
        messages.success(request, f"La matière '{libelle}' a été supprimée.")
        return redirect('pedagogie:matiere_list')
    return render(request, 'pedagogie/matiere_confirm_delete.html', {'matiere': matiere})


@login_required
def affectations_classe(request, pk):
    """Gère qui enseigne chaque matière dans une classe (titulaire par défaut au primaire)."""
    from grh.models import Personnel
    from .affectations import matieres_avec_enseignant, cycle_utilise_titulaire_par_defaut
    from .forms import AffectationEnseignementForm
    from .models import AffectationEnseignement

    ecole = request.user.ecole
    classe = get_object_or_404(
        Classe.objects.select_related('section', 'section__cycle', 'titulaire', 'ecole'),
        pk=pk,
        ecole=ecole,
    )
    rows = matieres_avec_enseignant(classe)
    form = AffectationEnseignementForm(ecole=ecole, classe=classe)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'supprimer':
            aff_id = request.POST.get('affectation_id')
            aff = get_object_or_404(AffectationEnseignement, pk=aff_id, classe=classe, ecole=ecole)
            matiere_lib = aff.matiere.libelle
            aff.delete()
            messages.success(
                request,
                f"Affectation retirée pour « {matiere_lib} ». "
                f"{'Le titulaire reprend le cours.' if cycle_utilise_titulaire_par_defaut(classe) else 'Enseignant de référence réappliqué.'}",
            )
            return redirect('pedagogie:affectations_classe', pk=classe.pk)

        form = AffectationEnseignementForm(request.POST, ecole=ecole, classe=classe)
        if form.is_valid():
            aff = form.save(commit=False)
            aff.ecole = ecole
            aff.classe = classe
            # Remplace une affectation existante pour la même matière
            AffectationEnseignement.objects.filter(classe=classe, matiere=aff.matiere).delete()
            aff.save()
            messages.success(
                request,
                f"« {aff.matiere.libelle} » confié(e) à {aff.enseignant.prenom} {aff.enseignant.nom} "
                f"pour la classe {classe.classe}.",
            )
            return redirect('pedagogie:affectations_classe', pk=classe.pk)

    return render(request, 'pedagogie/affectations_classe.html', {
        'classe': classe,
        'rows': rows,
        'form': form,
        'titulaire_defaut': cycle_utilise_titulaire_par_defaut(classe),
        'enseignants_count': Personnel.objects.filter(
            ecole=ecole,
            fonction__in=['Enseignant', 'Préfet', 'Directeur des études'],
        ).count(),
    })


STATUTS_PRESENCE = [c[0] for c in PresenceEleve.STATUT_CHOICES]


def _parse_date(raw, default=None):
    default = default or date.today()
    if not raw:
        return default
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return default


def _personnel_utilisateur(user):
    from grh.models import Personnel
    return Personnel.objects.filter(utilisateur=user).first()


def _peut_gerer_presence_classe(user, classe):
    """Seul le professeur titulaire de la classe peut faire l'appel."""
    from pedagogie.affectations import est_titulaire_classe

    personnel = _personnel_utilisateur(user)
    return est_titulaire_classe(personnel, classe)


def _presence_url(user, name, args=None):
    """Les présences élèves sont gérées uniquement via l'espace enseignant."""
    return reverse(f'utilisateur:{name}', args=args or ())


def _redirect_si_enseignant_hors_portail(request, name, args=None):
    """Les anciennes URLs pédagogie/presences ne sont plus exposées."""
    return None


def _ecole_presence(request):
    ecole = getattr(request.user, 'ecole', None)
    if ecole:
        return ecole
    personnel = _personnel_utilisateur(request.user)
    return personnel.ecole if personnel else None


@login_required
def presence_list(request):
    """Vue d'ensemble : état de l'appel quotidien par classe."""
    redir = _redirect_si_enseignant_hors_portail(request, 'presence_list')
    if redir:
        return redir

    ecole = _ecole_presence(request)
    if not ecole:
        messages.warning(request, "Aucune école associée à votre compte.")
        return redirect('utilisateur:enseignant_dashboard')

    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    filter_date = _parse_date(request.GET.get('date'))

    # Uniquement les classes dont l'utilisateur est titulaire
    personnel = _personnel_utilisateur(request.user)
    classes_qs = (
        Classe.objects.filter(ecole=ecole)
        .select_related('section', 'titulaire')
        .order_by('section__section', 'classe')
    )
    if not personnel:
        classes_qs = classes_qs.none()
    else:
        classes_qs = classes_qs.filter(titulaire=personnel)

    presences = {
        p.classe_id: p
        for p in PresenceClasse.objects.filter(
            ecole=ecole, date=filter_date
        ).prefetch_related('lignes')
    }

    rows = []
    for classe in classes_qs:
        nb_inscrits = 0
        if annee:
            nb_inscrits = Inscription.objects.filter(classe=classe, annee_s=annee).count()
        presence = presences.get(classe.id)
        rows.append({
            'classe': classe,
            'inscrits': nb_inscrits,
            'presence': presence,
            'presents': presence.nb_presents if presence else None,
            'absents': presence.nb_absents if presence else None,
            'retards': presence.nb_retards if presence else None,
            'excuses': presence.nb_excuses if presence else None,
            'fait': presence is not None,
        })

    return render(request, 'utilisateur/presence_list.html', {
        'rows': rows,
        'filter_date': filter_date,
        'annee_courante': annee,
        'total_faites': sum(1 for r in rows if r['fait']),
        'total_classes': len(rows),
    })


@login_required
def presence_classe(request, pk):
    """Liste de présence quotidienne des élèves d'une classe."""
    redir = _redirect_si_enseignant_hors_portail(request, 'presence_classe', args=[pk])
    if redir:
        return redir

    ecole = _ecole_presence(request)
    if not ecole:
        messages.warning(request, "Aucune école associée à votre compte.")
        return redirect('utilisateur:enseignant_dashboard')

    classe = get_object_or_404(
        Classe.objects.select_related('section', 'titulaire', 'ecole'),
        pk=pk,
        ecole=ecole,
    )
    if not _peut_gerer_presence_classe(request.user, classe):
        messages.error(
            request,
            "Seul le professeur titulaire de la classe peut faire l'appel.",
        )
        return redirect('utilisateur:enseignant_dashboard')

    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    filter_date = _parse_date(request.GET.get('date') or request.POST.get('date'))
    template = 'utilisateur/presence_classe.html'

    if not annee:
        messages.warning(request, "Aucune année scolaire en cours. Impossible de saisir la présence.")
        return render(request, template, {
            'classe': classe,
            'annee_courante': None,
            'filter_date': filter_date,
            'rows': [],
            'presence': None,
            'stats': {'presents': 0, 'absents': 0, 'retards': 0, 'excuses': 0, 'total': 0},
            'historique': [],
        })

    inscriptions = (
        Inscription.objects.filter(classe=classe, annee_s=annee)
        .select_related('eleve')
        .order_by('eleve__nom', 'eleve__prenom')
    )

    presence = (
        PresenceClasse.objects.filter(classe=classe, date=filter_date)
        .prefetch_related('lignes')
        .first()
    )
    lignes_map = {}
    if presence:
        lignes_map = {l.inscription_id: l for l in presence.lignes.all()}

    if request.method == 'POST':
        if presence:
            messages.warning(
                request,
                f"L'appel du {filter_date.strftime('%d/%m/%Y')} est déjà enregistré et ne peut plus être modifié.",
            )
            return redirect(
                f"{_presence_url(request.user, 'presence_classe', [classe.pk])}?date={filter_date.isoformat()}"
            )

        personnel = _personnel_utilisateur(request.user)
        presence = PresenceClasse.objects.create(
            classe=classe,
            date=filter_date,
            ecole=ecole,
            annee_scolaire=annee,
            saisi_par=personnel,
            remarque=(request.POST.get('remarque') or '').strip()[:255],
        )

        for ins in inscriptions:
            statut = request.POST.get(f'statut_{ins.id}', 'PRESENT')
            if statut not in STATUTS_PRESENCE:
                statut = 'PRESENT'
            commentaire = (request.POST.get(f'commentaire_{ins.id}') or '').strip()[:200]
            PresenceEleve.objects.create(
                presence_classe=presence,
                inscription=ins,
                statut=statut,
                commentaire=commentaire,
            )

        messages.success(
            request,
            f"Présence du {filter_date.strftime('%d/%m/%Y')} enregistrée pour la classe {classe.classe}.",
        )
        return redirect(
            f"{_presence_url(request.user, 'presence_classe', [classe.pk])}?date={filter_date.isoformat()}"
        )

    rows = []
    for ins in inscriptions:
        ligne = lignes_map.get(ins.id)
        rows.append({
            'inscription': ins,
            'statut': ligne.statut if ligne else 'PRESENT',
            'commentaire': ligne.commentaire if ligne else '',
        })

    stats = {
        'total': len(rows),
        'presents': sum(1 for r in rows if r['statut'] == 'PRESENT'),
        'absents': sum(1 for r in rows if r['statut'] == 'ABSENT'),
        'retards': sum(1 for r in rows if r['statut'] == 'RETARD'),
        'excuses': sum(1 for r in rows if r['statut'] == 'EXCUSE'),
    }

    historique = (
        PresenceClasse.objects.filter(classe=classe, annee_scolaire=annee)
        .order_by('-date')[:14]
    )

    return render(request, template, {
        'classe': classe,
        'annee_courante': annee,
        'filter_date': filter_date,
        'rows': rows,
        'presence': presence,
        'stats': stats,
        'historique': historique,
        'statuts': PresenceEleve.STATUT_CHOICES,
    })


def _recap_eleves_presence(classe, annee, inscriptions):
    """Agrège Présent/Absent/Retard/Excusé par inscription pour l'année."""
    stats_map = {}
    if annee and inscriptions:
        for row in (
            PresenceEleve.objects.filter(
                inscription__in=inscriptions,
                presence_classe__classe=classe,
                presence_classe__annee_scolaire=annee,
            )
            .values('inscription_id')
            .annotate(
                presents=Count('id', filter=Q(statut='PRESENT')),
                absents=Count('id', filter=Q(statut='ABSENT')),
                retards=Count('id', filter=Q(statut='RETARD')),
                excuses=Count('id', filter=Q(statut='EXCUSE')),
                total=Count('id'),
            )
        ):
            total = row['total'] or 0
            presents = row['presents'] or 0
            retards = row['retards'] or 0
            taux = round(((presents + retards) / total) * 100) if total else None
            stats_map[row['inscription_id']] = {
                'presents': presents,
                'absents': row['absents'] or 0,
                'retards': retards,
                'excuses': row['excuses'] or 0,
                'total': total,
                'taux': taux,
            }

    jours_appeles = 0
    if annee:
        jours_appeles = PresenceClasse.objects.filter(
            classe=classe, annee_scolaire=annee
        ).count()

    eleves_rows = []
    totaux = {'presents': 0, 'absents': 0, 'retards': 0, 'excuses': 0, 'total': 0}
    for ins in inscriptions:
        s = stats_map.get(ins.id, {
            'presents': 0, 'absents': 0, 'retards': 0, 'excuses': 0, 'total': 0, 'taux': None,
        })
        eleves_rows.append({'inscription': ins, 'eleve': ins.eleve, **s})
        for k in ('presents', 'absents', 'retards', 'excuses', 'total'):
            totaux[k] += s[k]

    taux_classe = None
    if totaux['total']:
        taux_classe = round(((totaux['presents'] + totaux['retards']) / totaux['total']) * 100)

    return eleves_rows, jours_appeles, totaux, taux_classe


@login_required
def presence_recap(request, pk):
    """Liste des élèves d'une classe avec récapitulatif de présence."""
    redir = _redirect_si_enseignant_hors_portail(request, 'presence_recap', args=[pk])
    if redir:
        return redir

    ecole = _ecole_presence(request)
    if not ecole:
        messages.warning(request, "Aucune école associée à votre compte.")
        return redirect('utilisateur:enseignant_dashboard')

    classe = get_object_or_404(
        Classe.objects.select_related('section', 'titulaire', 'ecole'),
        pk=pk,
        ecole=ecole,
    )
    if not _peut_gerer_presence_classe(request.user, classe):
        messages.error(
            request,
            "Seul le professeur titulaire de la classe peut consulter le récapitulatif d'appel.",
        )
        return redirect('utilisateur:enseignant_dashboard')

    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    if annee:
        inscriptions = (
            Inscription.objects.filter(classe=classe, annee_s=annee)
            .select_related('eleve', 'eleve__titeur')
            .order_by('eleve__nom', 'eleve__prenom')
        )
    else:
        inscriptions = Inscription.objects.none()

    eleves_rows, jours_appeles, totaux, taux_classe = _recap_eleves_presence(
        classe, annee, inscriptions
    )

    return render(request, 'utilisateur/presence_recap.html', {
        'classe': classe,
        'annee_courante': annee,
        'eleves_rows': eleves_rows,
        'jours_appeles': jours_appeles,
        'totaux': totaux,
        'taux_classe': taux_classe,
        'nb_eleves': len(eleves_rows),
    })
