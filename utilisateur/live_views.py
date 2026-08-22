"""Cours en direct (visioconférence Jitsi) — espaces enseignant et élève."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST

from inscription.models import Annee_Scolaire
from common.jitsi import build_jaas_jwt, external_api_script_url, is_jaas_enabled, meeting_domain, room_path
from pedagogie.affectations import peut_gerer_matiere_classes
from pedagogie.forms import CoursEnDirectForm
from pedagogie.models import CoursEnDirect, QuestionCoursDirect, qs_pour_classe
from utilisateur.cours_views import _require_eleve
from utilisateur.travaux_views import (
    _classes_enseignant,
    _matieres_enseignant,
    _require_enseignant,
)


def _direct_enseignant_qs(personnel):
    return (
        CoursEnDirect.objects.filter(ecole=personnel.ecole, enseignant=personnel)
        .select_related('classe', 'matiere', 'annee_scolaire', 'enseignant')
        .prefetch_related('classes')
        .order_by('-date_heure_prevue')
    )


def _peut_gerer_direct(personnel, seance):
    if seance.ecole_id != personnel.ecole_id:
        return False
    if seance.enseignant_id == personnel.id:
        return True
    return peut_gerer_matiere_classes(personnel, seance.matiere, seance.classes_concernees())


def _display_name(user):
    return (getattr(user, 'nom_complet', None) or user.get_username() or 'Participant').strip()


def _is_ajax(request):
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
    )


def _salle_tips(role):
    commun = [
        "Privilégiez Chrome ou Edge et une connexion Wi-Fi stable.",
        "Fermez les téléchargements et onglets vidéo inutiles avant de rejoindre la salle.",
        "Utilisez un casque pour réduire l'écho et améliorer l'intelligibilité.",
    ]
    if role == 'enseignant':
        return commun + [
            "Commencez avec micro coupé pour la classe puis donnez la parole progressivement.",
            "Épinglez les questions importantes pour garder le fil du cours.",
        ]
    return commun + [
        "Coupez votre caméra si la connexion devient lente, puis réactivez-la au besoin.",
        "Utilisez les signaux rapides pour demander une répétition ou signaler un souci de son.",
    ]


def _signaux_rapides(role):
    if role != 'eleve':
        return []
    return [
        "Main levée : je veux répondre",
        "Le son coupe chez moi",
        "Pouvez-vous répéter la consigne ?",
        "Pouvez-vous ralentir un peu ?",
        "J'ai terminé l'exercice",
    ]


def _acces_salle_enseignant(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return None, None, err
    seance = get_object_or_404(
        CoursEnDirect.objects.select_related('classe', 'matiere').prefetch_related('classes'),
        pk=pk,
        ecole=personnel.ecole,
    )
    if not _peut_gerer_direct(personnel, seance):
        if _is_ajax(request):
            return None, None, JsonResponse({'ok': False, 'error': 'Accès refusé.'}, status=403)
        messages.error(request, "Vous n'avez pas accès à cette séance.")
        return None, None, redirect('utilisateur:direct_enseignant_list')
    return personnel, seance, None


def _acces_salle_eleve(request, pk):
    eleve, inscription, err = _require_eleve(request)
    if err:
        return None, None, None, err
    seance = get_object_or_404(
        qs_pour_classe(
            CoursEnDirect.objects.select_related('classe', 'matiere', 'enseignant')
            .prefetch_related('classes'),
            inscription.classe,
        ),
        pk=pk,
        ecole=eleve.ecole,
        annee_scolaire=inscription.annee_s,
    )
    return eleve, inscription, seance, None


def _salle_context(request, seance, role, retour_url):
    debut = seance.date_heure_prevue
    fin = None
    if debut:
        fin = debut + timedelta(minutes=seance.duree_minutes or 60)
    display_name = _display_name(request.user)
    email = getattr(request.user, 'email', '') or ''
    est_enseignant = (role == 'enseignant')
    user_id = str(request.user.pk) if getattr(request.user, 'pk', None) else ''
    return {
        'seance': seance,
        'jitsi_url': seance.jitsi_embed_url(
            display_name,
            email=email,
            est_enseignant=est_enseignant,
            user_id=user_id,
        ),
        'jitsi_is_jaas': is_jaas_enabled(),
        'jitsi_domain': meeting_domain(),
        'jitsi_room_name': room_path(seance.room_name),
        'jitsi_script_url': external_api_script_url(),
        'jitsi_jwt': build_jaas_jwt(
            display_name,
            email,
            is_moderator=est_enseignant,
            user_id=user_id,
        ),
        'jitsi_display_name': display_name,
        'jitsi_email': email,
        'share_url': request.build_absolute_uri(),
        'role': role,
        'role_label': 'Enseignant' if role == 'enseignant' else 'Élève',
        'retour_url': retour_url,
        'questions_url': reverse('utilisateur:direct_questions', kwargs={'pk': seance.pk}),
        'question_create_url': reverse('utilisateur:direct_question_create', kwargs={'pk': seance.pk}),
        'salle_tips': _salle_tips(role),
        'signaux_rapides': _signaux_rapides(role),
        'debut_iso': debut.isoformat() if debut else '',
        'fin_iso': fin.isoformat() if fin else '',
        'now': timezone.now(),
    }


@login_required
def direct_enseignant_list(request):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    seances = list(_direct_enseignant_qs(personnel))
    statut = request.GET.get('statut')
    if statut:
        seances = [s for s in seances if s.statut == statut]

    now = timezone.now()
    seances_a_venir = sorted(
        [s for s in seances if s.date_heure_prevue and s.date_heure_prevue >= now],
        key=lambda s: s.date_heure_prevue,
    )

    return render(request, 'utilisateur/direct_enseignant_list.html', {
        'seances': seances,
        'filtre_statut': statut or '',
        'nb_planifies': sum(1 for s in seances if s.statut == CoursEnDirect.STATUT_PLANIFIE),
        'nb_en_cours': sum(1 for s in seances if s.statut == CoursEnDirect.STATUT_EN_COURS),
        'nb_a_venir': len(seances_a_venir),
        'prochaine_seance': seances_a_venir[0] if seances_a_venir else None,
        'now': now,
    })


@login_required
def direct_enseignant_create(request):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    ecole = personnel.ecole
    classes_qs = _classes_enseignant(personnel)
    matieres_qs = _matieres_enseignant(personnel)

    if request.method == 'POST':
        form = CoursEnDirectForm(
            request.POST, ecole=ecole, classes_qs=classes_qs, matieres_qs=matieres_qs
        )
        if form.is_valid():
            seance = form.save(commit=False)
            seance.ecole = ecole
            seance.enseignant = personnel
            if not peut_gerer_matiere_classes(
                personnel, seance.matiere, form.cleaned_data.get('classes')
            ):
                messages.error(
                    request,
                    "Vous ne pouvez pas planifier un cours pour cette classe / matière.",
                )
            else:
                seance.save()
                form.save_m2m()
                messages.success(request, "Séance de visioconférence planifiée.")
                return redirect('utilisateur:direct_enseignant_list')
    else:
        annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
        initial = {'annee_scolaire': annee, 'duree_minutes': 60}
        if request.GET.get('classe'):
            initial['classes'] = [request.GET.get('classe')]
        if request.GET.get('matiere'):
            initial['matiere'] = request.GET.get('matiere')
        form = CoursEnDirectForm(
            ecole=ecole, classes_qs=classes_qs, matieres_qs=matieres_qs, initial=initial
        )

    return render(request, 'utilisateur/direct_enseignant_form.html', {
        'form': form,
        'title': 'Nouveau cours en visioconférence',
        'seance': None,
    })


@login_required
def direct_enseignant_update(request, pk):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    seance = get_object_or_404(
        CoursEnDirect.objects.select_related('classe', 'matiere').prefetch_related('classes'),
        pk=pk,
        ecole=personnel.ecole,
    )
    if not _peut_gerer_direct(personnel, seance):
        messages.error(request, "Vous n'avez pas accès à cette séance.")
        return redirect('utilisateur:direct_enseignant_list')
    if seance.statut in (CoursEnDirect.STATUT_TERMINE, CoursEnDirect.STATUT_ANNULE):
        messages.warning(request, "Cette séance ne peut plus être modifiée.")
        return redirect('utilisateur:direct_enseignant_list')

    classes_qs = _classes_enseignant(personnel)
    matieres_qs = _matieres_enseignant(personnel)

    if request.method == 'POST':
        form = CoursEnDirectForm(
            request.POST,
            instance=seance,
            ecole=personnel.ecole,
            classes_qs=classes_qs,
            matieres_qs=matieres_qs,
        )
        if form.is_valid():
            updated = form.save(commit=False)
            if not peut_gerer_matiere_classes(
                personnel, updated.matiere, form.cleaned_data.get('classes')
            ):
                messages.error(
                    request,
                    "Vous ne pouvez pas planifier un cours pour cette classe / matière.",
                )
            else:
                updated.save()
                form.save_m2m()
                messages.success(request, "Séance mise à jour.")
                return redirect('utilisateur:direct_enseignant_list')
    else:
        form = CoursEnDirectForm(
            instance=seance,
            ecole=personnel.ecole,
            classes_qs=classes_qs,
            matieres_qs=matieres_qs,
        )

    return render(request, 'utilisateur/direct_enseignant_form.html', {
        'form': form,
        'title': 'Modifier la séance',
        'seance': seance,
    })


@login_required
def direct_enseignant_statut(request, pk, action):
    personnel, err = _require_enseignant(request)
    if err:
        return err

    seance = get_object_or_404(CoursEnDirect, pk=pk, ecole=personnel.ecole)
    if not _peut_gerer_direct(personnel, seance):
        messages.error(request, "Vous n'avez pas accès à cette séance.")
        return redirect('utilisateur:direct_enseignant_list')

    if request.method != 'POST':
        return redirect('utilisateur:direct_enseignant_list')

    mapping = {
        'demarrer': (CoursEnDirect.STATUT_EN_COURS, "Séance démarrée. Les élèves peuvent rejoindre."),
        'terminer': (CoursEnDirect.STATUT_TERMINE, "Séance terminée."),
        'annuler': (CoursEnDirect.STATUT_ANNULE, "Séance annulée."),
    }
    if action not in mapping:
        messages.error(request, "Action non reconnue.")
        return redirect('utilisateur:direct_enseignant_list')

    nouveau, msg = mapping[action]
    if action == 'demarrer' and seance.statut not in (
        CoursEnDirect.STATUT_PLANIFIE, CoursEnDirect.STATUT_EN_COURS
    ):
        messages.error(request, "Impossible de démarrer cette séance.")
        return redirect('utilisateur:direct_enseignant_list')
    if action == 'terminer' and seance.statut != CoursEnDirect.STATUT_EN_COURS:
        messages.error(request, "Seule une séance en cours peut être terminée.")
        return redirect('utilisateur:direct_enseignant_list')
    if action == 'annuler' and seance.statut in (
        CoursEnDirect.STATUT_TERMINE, CoursEnDirect.STATUT_ANNULE
    ):
        messages.error(request, "Cette séance est déjà clôturée.")
        return redirect('utilisateur:direct_enseignant_list')

    seance.statut = nouveau
    seance.save(update_fields=['statut', 'updated_at'])
    messages.success(request, msg)

    if action == 'demarrer':
        return redirect('utilisateur:direct_enseignant_salle', pk=seance.pk)
    return redirect('utilisateur:direct_enseignant_list')


@login_required
@xframe_options_sameorigin
def direct_enseignant_salle(request, pk):
    personnel, seance, err = _acces_salle_enseignant(request, pk)
    if err:
        return err
    if not seance.peut_etre_rejoint(est_enseignant=True):
        messages.warning(request, "Cette séance n'est plus accessible.")
        return redirect('utilisateur:direct_enseignant_list')

    if seance.statut == CoursEnDirect.STATUT_PLANIFIE:
        seance.statut = CoursEnDirect.STATUT_EN_COURS
        seance.save(update_fields=['statut', 'updated_at'])

    return render(
        request,
        'utilisateur/direct_salle.html',
        _salle_context(request, seance, 'enseignant', 'utilisateur:direct_enseignant_list'),
    )


@login_required
def direct_eleve_list(request):
    eleve, inscription, err = _require_eleve(request)
    if err:
        return err

    seances = list(
        qs_pour_classe(
            CoursEnDirect.objects.filter(
                ecole=eleve.ecole,
                annee_scolaire=inscription.annee_s,
                statut__in=[CoursEnDirect.STATUT_PLANIFIE, CoursEnDirect.STATUT_EN_COURS],
            ),
            inscription.classe,
        )
        .select_related('matiere', 'enseignant', 'classe')
        .prefetch_related('classes')
        .order_by('date_heure_prevue')
    )
    for s in seances:
        s.peut_rejoindre = s.peut_etre_rejoint(est_enseignant=False)
        s.est_imminente = bool(
            s.date_heure_prevue
            and 0 <= (s.date_heure_prevue - timezone.now()).total_seconds() <= 30 * 60
        )

    seances_a_venir = sorted(
        [s for s in seances if s.date_heure_prevue and s.date_heure_prevue >= timezone.now()],
        key=lambda s: s.date_heure_prevue,
    )

    return render(request, 'utilisateur/direct_eleve_list.html', {
        'seances': seances,
        'inscription': inscription,
        'nb_accessibles': sum(1 for s in seances if s.peut_rejoindre),
        'prochaine_seance': seances_a_venir[0] if seances_a_venir else None,
        'now': timezone.now(),
    })


@login_required
@xframe_options_sameorigin
def direct_eleve_salle(request, pk):
    eleve, inscription, seance, err = _acces_salle_eleve(request, pk)
    if err:
        return err
    if not seance.peut_etre_rejoint(est_enseignant=False):
        messages.warning(
            request,
            "La salle n'est pas encore ouverte. Attendez que l'enseignant démarre le cours "
            "(ou rejoignez 15 minutes avant l'horaire prévu).",
        )
        return redirect('utilisateur:direct_eleve_list')

    return render(
        request,
        'utilisateur/direct_salle.html',
        _salle_context(request, seance, 'eleve', 'utilisateur:direct_eleve_list'),
    )


def _peut_voir_questions(request, seance):
    if getattr(request.user, 'is_professeur', False):
        personnel, err = _require_enseignant(request)
        if err or not personnel:
            return False
        return _peut_gerer_direct(personnel, seance)
    if getattr(request.user, 'is_eleve', False):
        eleve = getattr(request.user, 'eleve', None)
        if not eleve:
            return False
        from utilisateur.views import _inscription_courante
        inscription = _inscription_courante(eleve)
        return bool(
            inscription
            and seance.ecole_id == eleve.ecole_id
            and seance.concerne_classe(inscription.classe)
            and seance.annee_scolaire_id == inscription.annee_s_id
        )
    return False


@login_required
@require_GET
def direct_questions(request, pk):
    seance = get_object_or_404(CoursEnDirect, pk=pk)
    if not _peut_voir_questions(request, seance):
        return JsonResponse({'ok': False, 'error': 'Accès refusé.'}, status=403)

    after_id = request.GET.get('after')
    qs = seance.questions.all().order_by('-epinglee', 'created_at')
    if after_id and str(after_id).isdigit():
        qs = qs.filter(id__gt=int(after_id))

    return JsonResponse({
        'ok': True,
        'questions': [q.to_dict() for q in qs[:100]],
        'count_ouvertes': seance.questions.filter(
            statut=QuestionCoursDirect.STATUT_OUVERTE
        ).count(),
    })


@login_required
@require_POST
def direct_question_create(request, pk):
    seance = get_object_or_404(CoursEnDirect, pk=pk)
    if not _peut_voir_questions(request, seance):
        return JsonResponse({'ok': False, 'error': 'Accès refusé.'}, status=403)
    if seance.statut in (CoursEnDirect.STATUT_TERMINE, CoursEnDirect.STATUT_ANNULE):
        return JsonResponse({'ok': False, 'error': 'La séance est terminée.'}, status=400)

    texte = (request.POST.get('texte') or '').strip()
    if len(texte) < 3:
        return JsonResponse(
            {'ok': False, 'error': 'Posez une question d’au moins 3 caractères.'},
            status=400,
        )
    if len(texte) > 1000:
        return JsonResponse({'ok': False, 'error': 'Question trop longue.'}, status=400)

    question = QuestionCoursDirect.objects.create(
        seance=seance,
        auteur=request.user,
        auteur_nom=_display_name(request.user),
        texte=texte,
    )
    return JsonResponse({'ok': True, 'question': question.to_dict()})


@login_required
@require_POST
def direct_question_action(request, pk, question_id, action):
    personnel, seance, err = _acces_salle_enseignant(request, pk)
    if err:
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'error': 'Accès refusé.'}, status=403)
        return err

    question = get_object_or_404(QuestionCoursDirect, pk=question_id, seance=seance)

    if action == 'repondre':
        reponse = (request.POST.get('reponse') or '').strip()
        if len(reponse) < 1:
            return JsonResponse({'ok': False, 'error': 'Saisissez une réponse.'}, status=400)
        question.reponse = reponse
        question.statut = QuestionCoursDirect.STATUT_REPONDUE
        question.repondu_at = timezone.now()
        question.save(update_fields=['reponse', 'statut', 'repondu_at'])
    elif action == 'marquer':
        question.statut = QuestionCoursDirect.STATUT_REPONDUE
        question.repondu_at = timezone.now()
        if not question.reponse:
            question.reponse = 'Répondu oralement pendant le cours.'
        question.save(update_fields=['reponse', 'statut', 'repondu_at'])
    elif action == 'epingler':
        question.epinglee = not question.epinglee
        question.save(update_fields=['epinglee'])
    else:
        return JsonResponse({'ok': False, 'error': 'Action inconnue.'}, status=400)

    return JsonResponse({'ok': True, 'question': question.to_dict()})
