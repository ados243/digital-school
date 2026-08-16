from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InscriptionForm


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('utilisateur:post_login')
    return redirect('utilisateur:login')


def inscription_view(request):
    if request.user.is_authenticated:
        return redirect('utilisateur:post_login')

    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"Bienvenue {user.prenom} ! Votre compte a été créé avec succès.")
            return redirect('utilisateur:post_login')
    else:
        form = InscriptionForm()

    return render(request, 'utilisateur/inscription.html', {'form': form})


@login_required
def post_login_redirect(request):
    user = request.user
    if user.is_parent or user.is_eleve:
        return redirect('utilisateur:portail')
    # Caissier en premier (rôle OU fonction GRH), avant les autres profils finance.
    if user.is_caissier and not user.is_superuser:
        return redirect('finances:paiement_list')
    if user.is_tresorerie_restreinte and not user.is_superuser:
        return redirect('finances:dashboard')
    if user.is_directeur_etudes and not user.is_superuser:
        return redirect('pedagogie:dashboard')
    if user.is_secretaire and not user.is_superuser:
        return redirect('inscription:dashboard')
    if user.is_prefet and not user.is_superuser:
        return redirect('grh:dashboard')
    if user.is_professeur and not user.is_superuser:
        return redirect('utilisateur:enseignant_dashboard')
    # Superuser, promoteur, manager, directeur… : tableau de bord Finances
    return redirect('finances:dashboard')


def _personnel_connecte(user):
    """Fiche Personnel liée au compte (corps professoral)."""
    from grh.models import Personnel
    return Personnel.objects.filter(utilisateur=user).select_related('ecole').first()


@login_required
def portail_view(request):
    user = request.user
    if user.is_professeur:
        return redirect('utilisateur:enseignant_dashboard')

    context = {}

    if user.is_parent:
        if not user.tuteur_id:
            context['enfants'] = []
        else:
            context['enfants'] = _enfants_parent_enrichis(user)
            context['tuteur'] = user.tuteur
            context['nb_inscrits'] = sum(1 for e in context['enfants'] if e['inscription'])

        from .direction_views import (
            communications_pour_parent,
            _rattacher_parent_aux_annonces_ecole,
        )
        from .models import CommunicationLecture

        _rattacher_parent_aux_annonces_ecole(user)
        annonces = list(communications_pour_parent(user)[:5])
        lus_ids = set(
            CommunicationLecture.objects.filter(
                parent=user,
                communication__in=annonces,
                lu_at__isnull=False,
            ).values_list('communication_id', flat=True)
        )
        context['annonces_recentes'] = [
            {'communication': c, 'lu': c.id in lus_ids} for c in annonces
        ]
        context['nb_annonces_non_lues'] = sum(1 for a in context['annonces_recentes'] if not a['lu'])

    elif user.is_eleve and user.eleve_id:
        from inscription.models import Inscription
        from pedagogie.models import NoteEleve

        inscriptions = (
            Inscription.objects.filter(eleve=user.eleve)
            .select_related('classe', 'annee_s')
            .order_by('-date')
        )
        context['inscription_courante'] = inscriptions.first()
        context['notes_recentes'] = (
            NoteEleve.objects.filter(inscription__in=inscriptions)
            .exclude(note__isnull=True)
            .select_related('travail', 'travail__matiere')
            .order_by('-travail__date_travail')[:10]
        )

    return render(request, 'utilisateur/portail.html', context)


def _inscription_courante(eleve):
    """Inscription de l'année scolaire en cours, sinon la plus récente."""
    from inscription.models import Annee_Scolaire, Inscription

    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    qs = (
        Inscription.objects.filter(eleve=eleve)
        .select_related('classe', 'classe__section', 'classe__titulaire', 'annee_s')
        .order_by('-date')
    )
    if annee:
        courante = qs.filter(annee_s=annee).first()
        if courante:
            return courante
    return qs.first()


def _stats_presence_inscription(inscription):
    from django.db.models import Count, Q
    from pedagogie.models import PresenceEleve, PresenceClasse

    if not inscription:
        return {
            'presents': 0, 'absents': 0, 'retards': 0, 'excuses': 0,
            'total': 0, 'taux': None, 'jours_appeles': 0,
        }

    row = (
        PresenceEleve.objects.filter(
            inscription=inscription,
            presence_classe__annee_scolaire=inscription.annee_s,
        )
        .aggregate(
            presents=Count('id', filter=Q(statut='PRESENT')),
            absents=Count('id', filter=Q(statut='ABSENT')),
            retards=Count('id', filter=Q(statut='RETARD')),
            excuses=Count('id', filter=Q(statut='EXCUSE')),
            total=Count('id'),
        )
    )
    total = row['total'] or 0
    presents = row['presents'] or 0
    retards = row['retards'] or 0
    taux = round(((presents + retards) / total) * 100) if total else None
    jours = PresenceClasse.objects.filter(
        classe=inscription.classe,
        annee_scolaire=inscription.annee_s,
    ).count()
    return {
        'presents': presents,
        'absents': row['absents'] or 0,
        'retards': retards,
        'excuses': row['excuses'] or 0,
        'total': total,
        'taux': taux,
        'jours_appeles': jours,
    }


def _finances_inscription(inscription):
    """Soldes frais + derniers paiements pour une inscription."""
    from decimal import Decimal
    from finances.models import Paiement
    from finances.paiement_utils import frais_disponibles_pour_inscription, paiements_valides_par_frais, solde_frais
    from finances.tenant import frais_for_ecole

    if not inscription:
        return {
            'frais_dus': [],
            'paiements': [],
            'total_du': Decimal('0'),
            'nb_impayes': 0,
            'frais_inscription_ok': False,
        }

    ecole = inscription.eleve.ecole
    frais_dus = frais_disponibles_pour_inscription(ecole, inscription)
    total_du = sum((f['reste'] for f in frais_dus), Decimal('0'))

    # Vue complète des frais (soldés inclus) pour le détail
    paye_par_frais = paiements_valides_par_frais(ecole)
    frais_qs = frais_for_ecole(ecole).filter(
        section_id=inscription.classe.section_id,
        annee=inscription.annee_s,
    ).select_related('type_frais', 'devise')
    frais_rows = []
    for frais in frais_qs:
        solde = solde_frais(frais, inscription.id, paye_par_frais)
        frais_rows.append({'frais': frais, **solde})

    paiements = (
        Paiement.objects.filter(eleve=inscription)
        .select_related('frais', 'frais__type_frais', 'devise')
        .order_by('-date_encodage')[:12]
    )

    return {
        'frais_dus': frais_dus,
        'frais_rows': frais_rows,
        'paiements': paiements,
        'total_du': total_du,
        'nb_impayes': len(frais_dus),
        'frais_inscription_ok': bool(inscription.frais_inscription),
    }


def _enfants_parent_enrichis(user):
    """Liste des enfants du tuteur avec inscription, présence et finance résumé."""
    from inscription.models import Eleve
    from pedagogie.models import NoteEleve

    enfants = list(
        Eleve.objects.filter(titeur=user.tuteur)
        .select_related('ecole')
        .order_by('nom', 'prenom')
    )
    result = []
    for eleve in enfants:
        inscription = _inscription_courante(eleve)
        presence = _stats_presence_inscription(inscription)
        finances = _finances_inscription(inscription)
        notes_count = 0
        if inscription:
            notes_count = (
                NoteEleve.objects.filter(inscription=inscription)
                .exclude(note__isnull=True)
                .count()
            )
        result.append({
            'eleve': eleve,
            'inscription': inscription,
            'presence': presence,
            'finances': finances,
            'notes_count': notes_count,
        })
    return result


@login_required
def parent_enfant_detail(request, pk):
    """Suivi détaillé d'un enfant pour le parent connecté."""
    if not request.user.is_parent or not request.user.tuteur_id:
        return redirect('utilisateur:portail')

    from inscription.models import Eleve
    from pedagogie.models import NoteEleve, PresenceEleve, Matiere

    eleve = get_object_or_404(
        Eleve.objects.select_related('ecole', 'titeur'),
        pk=pk,
        titeur=request.user.tuteur,
    )
    inscription = _inscription_courante(eleve)
    presence = _stats_presence_inscription(inscription)
    finances = _finances_inscription(inscription)

    notes = []
    presences_recentes = []
    matieres = []
    if inscription:
        notes = list(
            NoteEleve.objects.filter(inscription=inscription)
            .select_related('travail', 'travail__matiere')
            .order_by('-travail__date_travail', '-id')[:30]
        )
        presences_recentes = list(
            PresenceEleve.objects.filter(
                inscription=inscription,
                presence_classe__annee_scolaire=inscription.annee_s,
            )
            .select_related('presence_classe')
            .order_by('-presence_classe__date')[:20]
        )
        matieres = list(
            Matiere.objects.filter(
                ecole=eleve.ecole,
                section=inscription.classe.section,
            )
            .select_related('enserignant')
            .order_by('libelle')
        )

    return render(request, 'utilisateur/parent_enfant.html', {
        'eleve': eleve,
        'inscription': inscription,
        'presence': presence,
        'finances': finances,
        'notes': notes,
        'presences_recentes': presences_recentes,
        'matieres': matieres,
        'titulaire': inscription.classe.titulaire if inscription else None,
    })


@login_required
def enseignant_dashboard(request):
    """Espace du professeur : classes titulaire / cours affectés et aperçu des effectifs."""
    if not request.user.is_professeur:
        return redirect('utilisateur:post_login')

    from inscription.models import Annee_Scolaire, Classe, Inscription
    from pedagogie.affectations import travaux_accessibles_qs
    from pedagogie.models import AffectationEnseignement, Matiere, TravailCote

    personnel = _personnel_connecte(request.user)
    if not personnel:
        return render(request, 'utilisateur/enseignant_dashboard.html', {
            'personnel': None,
            'classes_data': [],
            'annee_courante': None,
            'matieres': [],
            'travaux_recents': [],
            'total_eleves': 0,
            'total_classes': 0,
        })

    ecole = personnel.ecole
    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()

    aff_classe_ids = AffectationEnseignement.objects.filter(
        enseignant=personnel, ecole=ecole
    ).values_list('classe_id', flat=True)
    sections_ref = Matiere.objects.filter(
        ecole=ecole, enserignant=personnel
    ).values_list('section_id', flat=True)

    classes = (
        Classe.objects.filter(ecole=ecole)
        .filter(
            Q(titulaire=personnel)
            | Q(id__in=aff_classe_ids)
            | Q(section_id__in=sections_ref)
        )
        .select_related('section', 'section__cycle', 'titulaire')
        .distinct()
        .order_by('section__section', 'classe')
    )

    classes_data = []
    total_eleves = 0
    for classe in classes:
        if annee:
            inscrits_qs = (
                Inscription.objects.filter(classe=classe, annee_s=annee)
                .select_related('eleve', 'eleve__titeur')
                .order_by('eleve__nom', 'eleve__prenom')
            )
            eleves = [ins.eleve for ins in inscrits_qs]
            inscrits = len(eleves)
            garcons = sum(1 for e in eleves if e.sexe == 'Masculin')
            filles = sum(1 for e in eleves if e.sexe == 'Feminin')
        else:
            eleves = []
            inscrits = garcons = filles = 0
        total_eleves += inscrits
        percent = int((inscrits / classe.capacite_max) * 100) if classe.capacite_max else 0
        role = 'titulaire' if classe.titulaire_id == personnel.id else 'cours'
        classes_data.append({
            'classe': classe,
            'inscrits': inscrits,
            'garcons': garcons,
            'filles': filles,
            'percent': percent,
            'places': max(classe.capacite_max - inscrits, 0),
            'eleves': eleves,
            'role': role,
        })

    matieres = (
        Matiere.objects.filter(ecole=ecole)
        .filter(
            Q(enserignant=personnel)
            | Q(affectations_classes__enseignant=personnel)
            | Q(section_id__in=Classe.objects.filter(
                ecole=ecole, titulaire=personnel
            ).values_list('section_id', flat=True))
        )
        .select_related('section')
        .distinct()
        .order_by('section__section', 'libelle')
    )

    travaux_recents = (
        travaux_accessibles_qs(
            personnel,
            TravailCote.objects.filter(ecole=ecole).select_related('matiere', 'classe'),
        )
        .order_by('-date_travail', '-id')[:8]
    )

    return render(request, 'utilisateur/enseignant_dashboard.html', {
        'personnel': personnel,
        'classes_data': classes_data,
        'annee_courante': annee,
        'matieres': matieres,
        'travaux_recents': travaux_recents,
        'total_eleves': total_eleves,
        'total_classes': len(classes_data),
    })


@login_required
def enseignant_classe_detail(request, pk):
    """Détail d'une classe dont l'utilisateur est titulaire : liste des élèves."""
    if not request.user.is_professeur:
        return redirect('utilisateur:post_login')

    from inscription.models import Annee_Scolaire, Classe, Inscription
    from pedagogie.affectations import matieres_avec_enseignant, travaux_accessibles_qs
    from pedagogie.models import AffectationEnseignement, Matiere, TravailCote
    from pedagogie.views import _recap_eleves_presence

    personnel = _personnel_connecte(request.user)
    if not personnel:
        messages.warning(request, "Aucune fiche personnel n'est rattachée à votre compte.")
        return redirect('utilisateur:enseignant_dashboard')

    classe = get_object_or_404(
        Classe.objects.select_related('section', 'section__cycle', 'ecole', 'titulaire'),
        pk=pk,
        ecole=personnel.ecole,
    )
    est_titulaire = classe.titulaire_id == personnel.id
    a_un_cours = AffectationEnseignement.objects.filter(
        classe=classe, enseignant=personnel
    ).exists()
    a_ref_section = Matiere.objects.filter(
        ecole=personnel.ecole, section=classe.section, enserignant=personnel
    ).exists()
    if not (est_titulaire or a_un_cours or a_ref_section):
        messages.error(request, "Vous n'avez pas accès à cette classe.")
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

    # Présences et bulletins : réservés au titulaire de la classe
    jours_appeles = 0
    presence_totaux = None
    taux_classe = None
    bulletins_map = {}
    if est_titulaire:
        eleves_presence, jours_appeles, presence_totaux, taux_classe = _recap_eleves_presence(
            classe, annee, inscriptions
        )
        if annee and inscriptions:
            from pedagogie.bulletin import assurer_bulletins_classe
            for b in assurer_bulletins_classe(classe, annee):
                bulletins_map[b.inscription_id] = b
        eleves_rows = [
            {
                **row,
                'tuteur': row['eleve'].titeur,
                'bulletin': bulletins_map.get(row['inscription'].id),
            }
            for row in eleves_presence
        ]
    else:
        eleves_rows = [
            {
                'inscription': ins,
                'eleve': ins.eleve,
                'tuteur': ins.eleve.titeur,
                'presents': 0,
                'absents': 0,
                'retards': 0,
                'excuses': 0,
                'taux': None,
                'bulletin': None,
            }
            for ins in inscriptions
        ]

    matieres_rows = matieres_avec_enseignant(classe)
    if not est_titulaire:
        matieres_rows = [
            r for r in matieres_rows
            if r['enseignant'] and r['enseignant'].id == personnel.id
        ]
    travaux = (
        travaux_accessibles_qs(
            personnel,
            TravailCote.objects.filter(classe=classe, ecole=personnel.ecole)
            .select_related('matiere'),
        )
        .order_by('-date_travail')[:10]
    )

    return render(request, 'utilisateur/enseignant_classe.html', {
        'personnel': personnel,
        'classe': classe,
        'annee_courante': annee,
        'eleves_rows': eleves_rows,
        'inscrits': len(eleves_rows),
        'garcons': sum(1 for r in eleves_rows if r['eleve'].sexe == 'Masculin'),
        'filles': sum(1 for r in eleves_rows if r['eleve'].sexe == 'Feminin'),
        'places_restantes': max(classe.capacite_max - len(eleves_rows), 0),
        'matieres': matieres_rows,
        'travaux': travaux,
        'jours_appeles': jours_appeles,
        'presence_totaux': presence_totaux,
        'taux_classe': taux_classe,
        'est_titulaire': est_titulaire,
    })
