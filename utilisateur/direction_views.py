"""Communications direction → parents (ciblage parent / classe / section / école)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from inscription.models import Annee_Scolaire, Classe, Eleve, Inscription, Section
from .models import CommunicationDirection, CommunicationLecture, Utilisateur


def _ecole_staff(user):
    return getattr(user, 'ecole', None)


def _est_direction(user):
    """Staff interne pouvant communiquer au nom de la direction."""
    if not user.is_authenticated:
        return False
    if user.is_parent or user.is_eleve or user.is_professeur:
        return False
    return bool(user.ecole_id)


def _annee_courante(ecole):
    return Annee_Scolaire.objects.filter(est_encoure=True).first()


def _parents_ecole(ecole):
    """Tous les comptes parent rattachés à l'école (via tuteur, compte ou enfants)."""
    tuteur_ids = set(
        Eleve.objects.filter(ecole=ecole).values_list('titeur_id', flat=True)
    )
    tuteur_ids.update(
        Utilisateur.objects.filter(role='PARENT', tuteur__ecole=ecole)
        .values_list('tuteur_id', flat=True)
    )
    return Utilisateur.objects.filter(role='PARENT').filter(
        Q(tuteur_id__in=tuteur_ids) | Q(ecole=ecole) | Q(tuteur__ecole=ecole)
    ).distinct()


def _tuteurs_ids_pour_inscriptions(inscriptions_qs):
    return set(
        inscriptions_qs.exclude(eleve__titeur_id=None)
        .values_list('eleve__titeur_id', flat=True)
        .distinct()
    )


def resoudre_destinataires(communication):
    """Retourne le queryset des Utilisateur parents ciblés."""
    ecole = communication.ecole
    annee = _annee_courante(ecole)
    cible = communication.cible_type

    if cible == CommunicationDirection.CIBLE_PARENT:
        if communication.cible_parent_id:
            return Utilisateur.objects.filter(pk=communication.cible_parent_id, role='PARENT')
        return Utilisateur.objects.none()

    if cible == CommunicationDirection.CIBLE_ECOLE:
        return _parents_ecole(ecole)

    # Classe / section : privilégier l'année en cours, sinon toutes les inscriptions
    inscriptions = Inscription.objects.filter(eleve__ecole=ecole)
    if annee:
        inscriptions = inscriptions.filter(annee_s=annee)

    if cible == CommunicationDirection.CIBLE_CLASSE and communication.cible_classe_id:
        inscriptions = inscriptions.filter(classe_id=communication.cible_classe_id)
    elif cible == CommunicationDirection.CIBLE_SECTION and communication.cible_section_id:
        inscriptions = inscriptions.filter(classe__section_id=communication.cible_section_id)
    else:
        return Utilisateur.objects.none()

    # Si aucune inscription année en cours, élargir sans filtre d'année
    if annee and not inscriptions.exists():
        inscriptions = Inscription.objects.filter(eleve__ecole=ecole)
        if cible == CommunicationDirection.CIBLE_CLASSE:
            inscriptions = inscriptions.filter(classe_id=communication.cible_classe_id)
        else:
            inscriptions = inscriptions.filter(classe__section_id=communication.cible_section_id)

    tuteur_ids = _tuteurs_ids_pour_inscriptions(inscriptions)
    if not tuteur_ids:
        return Utilisateur.objects.none()
    return Utilisateur.objects.filter(role='PARENT', tuteur_id__in=tuteur_ids).distinct()


def enregistrer_destinataires(communication):
    """Fige les destinataires au moment de l'envoi."""
    parents = list(resoudre_destinataires(communication))
    existing = set(
        CommunicationLecture.objects.filter(communication=communication)
        .values_list('parent_id', flat=True)
    )
    to_create = [
        CommunicationLecture(communication=communication, parent=p)
        for p in parents
        if p.id not in existing
    ]
    if to_create:
        CommunicationLecture.objects.bulk_create(to_create, ignore_conflicts=True)
    return len(parents)


def communications_pour_parent(user):
    """Communications visibles par un parent connecté."""
    if not getattr(user, 'is_parent', False):
        return CommunicationDirection.objects.none()

    # 1) Via destinataires figés à l'envoi (source de vérité)
    ids_figes = list(
        CommunicationLecture.objects.filter(parent=user)
        .values_list('communication_id', flat=True)
    )

    # 2) Filet de sécurité : recalcul dynamique (nouveaux comptes / anciens messages)
    ecole_ids = set()
    if user.ecole_id:
        ecole_ids.add(user.ecole_id)
    if user.tuteur_id:
        ecole_ids.add(user.tuteur.ecole_id)
        for eid in Eleve.objects.filter(titeur_id=user.tuteur_id).values_list('ecole_id', flat=True):
            ecole_ids.add(eid)

    q = Q(pk__in=ids_figes) if ids_figes else Q(pk__in=[])

    if ecole_ids:
        q |= Q(cible_type=CommunicationDirection.CIBLE_ECOLE, ecole_id__in=ecole_ids)
        q |= Q(cible_type=CommunicationDirection.CIBLE_PARENT, cible_parent=user)

        inscriptions = Inscription.objects.filter(eleve__titeur_id=user.tuteur_id) if user.tuteur_id else Inscription.objects.none()
        classe_ids = set(inscriptions.values_list('classe_id', flat=True))
        section_ids = set(inscriptions.values_list('classe__section_id', flat=True))
        if classe_ids:
            q |= Q(
                cible_type=CommunicationDirection.CIBLE_CLASSE,
                cible_classe_id__in=classe_ids,
                ecole_id__in=ecole_ids,
            )
        if section_ids:
            q |= Q(
                cible_type=CommunicationDirection.CIBLE_SECTION,
                cible_section_id__in=section_ids,
                ecole_id__in=ecole_ids,
            )

    return (
        CommunicationDirection.objects.filter(q)
        .select_related('auteur', 'cible_parent', 'cible_classe', 'cible_section', 'ecole')
        .distinct()
    )


@login_required
def direction_communication_list(request):
    if not _est_direction(request.user):
        messages.error(request, "Accès réservé à la direction.")
        return redirect('utilisateur:post_login')

    ecole = _ecole_staff(request.user)
    communications = (
        CommunicationDirection.objects.filter(ecole=ecole)
        .select_related('auteur', 'cible_parent', 'cible_classe', 'cible_section')
    )
    rows = []
    for com in communications:
        # S'assurer que les anciens messages ont bien des destinataires
        if not com.lectures.exists():
            enregistrer_destinataires(com)
        nb_dest = com.lectures.count()
        nb_lus = com.lectures.exclude(lu_at__isnull=True).count()
        rows.append({
            'communication': com,
            'nb_destinataires': nb_dest,
            'nb_lus': nb_lus,
        })

    return render(request, 'utilisateur/direction_communication_list.html', {
        'rows': rows,
        'ecole': ecole,
    })


@login_required
def direction_communication_create(request):
    if not _est_direction(request.user):
        messages.error(request, "Accès réservé à la direction.")
        return redirect('utilisateur:post_login')

    ecole = _ecole_staff(request.user)
    annee = _annee_courante(ecole)

    parents = _parents_ecole(ecole).select_related('tuteur').order_by('prenom', 'last_name')
    classes = (
        Classe.objects.filter(ecole=ecole)
        .select_related('section')
        .order_by('section__section', 'classe')
    )
    section_ids = classes.values_list('section_id', flat=True).distinct()
    sections = Section.objects.filter(id__in=section_ids).order_by('section')

    form_errors = []
    initial = {
        'sujet': '',
        'contenu': '',
        'cible_type': CommunicationDirection.CIBLE_ECOLE,
        'cible_parent': '',
        'cible_classe': '',
        'cible_section': '',
    }

    if request.method == 'POST':
        sujet = (request.POST.get('sujet') or '').strip()
        contenu = (request.POST.get('contenu') or '').strip()
        cible_type = request.POST.get('cible_type') or CommunicationDirection.CIBLE_ECOLE
        cible_parent_id = request.POST.get('cible_parent') or None
        cible_classe_id = request.POST.get('cible_classe') or None
        cible_section_id = request.POST.get('cible_section') or None

        initial.update({
            'sujet': sujet,
            'contenu': contenu,
            'cible_type': cible_type,
            'cible_parent': cible_parent_id or '',
            'cible_classe': cible_classe_id or '',
            'cible_section': cible_section_id or '',
        })

        if not sujet or not contenu:
            form_errors.append("Le sujet et le message sont obligatoires.")
        if cible_type not in dict(CommunicationDirection.CIBLE_CHOICES):
            form_errors.append("Type de destinataire invalide.")

        cible_parent = None
        cible_classe = None
        cible_section = None

        if not form_errors:
            if cible_type == CommunicationDirection.CIBLE_PARENT:
                if not cible_parent_id:
                    form_errors.append("Sélectionnez un parent.")
                else:
                    cible_parent = parents.filter(pk=cible_parent_id).first()
                    if not cible_parent:
                        form_errors.append("Parent introuvable.")
            elif cible_type == CommunicationDirection.CIBLE_CLASSE:
                if not cible_classe_id:
                    form_errors.append("Sélectionnez une classe.")
                else:
                    cible_classe = classes.filter(pk=cible_classe_id).first()
                    if not cible_classe:
                        form_errors.append("Classe introuvable.")
            elif cible_type == CommunicationDirection.CIBLE_SECTION:
                if not cible_section_id:
                    form_errors.append("Sélectionnez une section.")
                else:
                    cible_section = sections.filter(pk=cible_section_id).first()
                    if not cible_section:
                        form_errors.append("Section introuvable.")

        if not form_errors:
            com = CommunicationDirection.objects.create(
                ecole=ecole,
                auteur=request.user,
                sujet=sujet[:200],
                contenu=contenu,
                cible_type=cible_type,
                cible_parent=cible_parent,
                cible_classe=cible_classe,
                cible_section=cible_section,
            )
            nb = enregistrer_destinataires(com)
            wa_stats = {"envoyes": 0, "echecs": 0, "ignores": 0}
            try:
                from finances.whatsapp import notifier_communication_whatsapp

                wa_stats = notifier_communication_whatsapp(com)
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "Envoi WhatsApp communication %s échoué", com.pk
                )

            if nb == 0:
                messages.warning(
                    request,
                    "Communication enregistrée, mais aucun compte parent correspondant n'a été trouvé. "
                    "Les parents doivent avoir créé leur compte (matricule tuteur) pour recevoir les messages.",
                )
            else:
                extra_wa = ""
                if wa_stats.get("envoyes") or wa_stats.get("echecs") or wa_stats.get("ignores"):
                    extra_wa = (
                        f" WhatsApp : {wa_stats.get('envoyes', 0)} envoyé(s), "
                        f"{wa_stats.get('echecs', 0)} échec(s), "
                        f"{wa_stats.get('ignores', 0)} sans numéro."
                    )
                messages.success(
                    request,
                    f"Communication envoyée à {nb} parent{'' if nb == 1 else 's'} "
                    f"({com.libelle_cible}).{extra_wa}",
                )
            return redirect('utilisateur:direction_communication_list')

        for err in form_errors:
            messages.error(request, err)

    return render(request, 'utilisateur/direction_communication_form.html', {
        'parents': parents,
        'classes': classes,
        'sections': sections,
        'annee_courante': annee,
        'ecole': ecole,
        'cible_choices': CommunicationDirection.CIBLE_CHOICES,
        'form': initial,
    })


@login_required
def direction_communication_detail(request, pk):
    if not _est_direction(request.user):
        messages.error(request, "Accès réservé à la direction.")
        return redirect('utilisateur:post_login')

    ecole = _ecole_staff(request.user)
    com = get_object_or_404(
        CommunicationDirection.objects.select_related(
            'auteur', 'cible_parent', 'cible_classe', 'cible_section', 'ecole'
        ),
        pk=pk,
        ecole=ecole,
    )
    if not com.lectures.exists():
        enregistrer_destinataires(com)

    dest_rows = [
        {
            'parent': lec.parent,
            'lu': lec if lec.lu_at else None,
            'lecture': lec,
        }
        for lec in com.lectures.select_related('parent', 'parent__tuteur').order_by(
            'parent__prenom', 'parent__last_name'
        )
    ]

    return render(request, 'utilisateur/direction_communication_detail.html', {
        'communication': com,
        'dest_rows': dest_rows,
        'nb_destinataires': len(dest_rows),
        'nb_lus': sum(1 for r in dest_rows if r['lu']),
    })


@login_required
def parent_annonces_list(request):
    if not request.user.is_parent:
        return redirect('utilisateur:portail')

    # Rattrapage : rattacher ce parent aux communications ECOLE déjà envoyées
    _rattacher_parent_aux_annonces_ecole(request.user)

    qs = communications_pour_parent(request.user)
    lus_ids = set(
        CommunicationLecture.objects.filter(
            parent=request.user,
            communication__in=qs,
            lu_at__isnull=False,
        ).values_list('communication_id', flat=True)
    )
    rows = [
        {'communication': c, 'lu': c.id in lus_ids}
        for c in qs
    ]
    return render(request, 'utilisateur/parent_annonces.html', {
        'rows': rows,
        'nb_non_lus': sum(1 for r in rows if not r['lu']),
    })


@login_required
def parent_annonce_detail(request, pk):
    if not request.user.is_parent:
        return redirect('utilisateur:portail')

    _rattacher_parent_aux_annonces_ecole(request.user)

    qs = communications_pour_parent(request.user)
    com = get_object_or_404(qs, pk=pk)
    lecture, _ = CommunicationLecture.objects.get_or_create(
        communication=com,
        parent=request.user,
    )
    if lecture.lu_at is None:
        lecture.lu_at = timezone.now()
        lecture.save(update_fields=['lu_at'])

    return render(request, 'utilisateur/parent_annonce_detail.html', {
        'communication': com,
    })


def _rattacher_parent_aux_annonces_ecole(user):
    """Assure qu'un parent voit les annonces école déjà envoyées."""
    if not user.tuteur_id and not user.ecole_id:
        return
    ecole_ids = set()
    if user.ecole_id:
        ecole_ids.add(user.ecole_id)
    if user.tuteur_id:
        ecole_ids.add(user.tuteur.ecole_id)

    manquantes = CommunicationDirection.objects.filter(
        cible_type=CommunicationDirection.CIBLE_ECOLE,
        ecole_id__in=ecole_ids,
    ).exclude(lectures__parent=user)

    CommunicationLecture.objects.bulk_create(
        [CommunicationLecture(communication=c, parent=user) for c in manquantes],
        ignore_conflicts=True,
    )
