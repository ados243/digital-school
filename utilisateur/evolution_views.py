"""Évolution des élèves pour le professeur (cours qu'il enseigne)."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from inscription.models import Annee_Scolaire, Classe, Inscription
from pedagogie.affectations import (
    matieres_avec_enseignant,
    peut_gerer_matiere_classe,
    travaux_accessibles_qs,
)
from pedagogie.models import AffectationEnseignement, Matiere, NoteEleve, TravailCote


def _personnel(user):
    from grh.models import Personnel
    return Personnel.objects.filter(utilisateur=user).select_related('ecole').first()


def _peut_voir_classe(personnel, classe):
    if classe.ecole_id != personnel.ecole_id:
        return False
    if classe.titulaire_id == personnel.id:
        return True
    if AffectationEnseignement.objects.filter(classe=classe, enseignant=personnel).exists():
        return True
    return Matiere.objects.filter(
        ecole=personnel.ecole, section=classe.section, enserignant=personnel
    ).exists()


def _matieres_cours(personnel, classe):
    """Matières que le professeur enseigne réellement dans cette classe."""
    rows = matieres_avec_enseignant(classe)
    return [
        r['matiere']
        for r in rows
        if peut_gerer_matiere_classe(personnel, r['matiere'], classe)
    ]


def _to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tendance(notes_sur_20):
    """Compare la moyenne de la 1re moitié et de la 2e moitié des notes (/20)."""
    vals = [n for n in notes_sur_20 if n is not None]
    if len(vals) < 2:
        return 'indetermine', None
    mid = max(1, len(vals) // 2)
    debut = sum(vals[:mid]) / mid
    fin = sum(vals[mid:]) / (len(vals) - mid)
    delta = fin - debut
    if delta >= 0.5:
        return 'hausse', round(delta, 2)
    if delta <= -0.5:
        return 'baisse', round(delta, 2)
    return 'stable', round(delta, 2)


def _moyenne_ponderee(points):
    """points = list of (note_sur_20, coefficient)."""
    total = Decimal('0')
    poids = Decimal('0')
    for note, coef in points:
        if note is None:
            continue
        c = Decimal(str(coef or 1))
        total += Decimal(str(note)) * c
        poids += c
    if poids <= 0:
        return None
    return round(float(total / poids), 2)


def _construire_evolution(personnel, classe, annee, matiere=None):
    matieres = _matieres_cours(personnel, classe)
    if matiere:
        matieres = [m for m in matieres if m.id == matiere.id]

    travaux_qs = travaux_accessibles_qs(
        personnel,
        TravailCote.objects.filter(
            ecole=personnel.ecole,
            classe=classe,
            annee_scolaire=annee,
            matiere__in=matieres,
        ).select_related('matiere', 'periode', 'division'),
    ).order_by('date_travail', 'id')

    travaux = list(travaux_qs)
    inscriptions = list(
        Inscription.objects.filter(classe=classe, annee_s=annee)
        .select_related('eleve')
        .order_by('eleve__nom', 'eleve__prenom')
    )

    notes = NoteEleve.objects.filter(
        travail__in=travaux,
        inscription__in=inscriptions,
    ).select_related('travail', 'travail__matiere')

    notes_map = {}
    for n in notes:
        notes_map.setdefault(n.inscription_id, {})[n.travail_id] = n

    eleves = []
    for ins in inscriptions:
        serie = []
        points_moy = []
        for t in travaux:
            n = notes_map.get(ins.id, {}).get(t.id)
            if n is None or n.absent:
                serie.append({
                    'travail_id': t.id,
                    'date': t.date_travail,
                    'label': t.titre or t.get_type_travail_display(),
                    'matiere': t.matiere.libelle,
                    'note': None,
                    'sur_20': None,
                    'absent': bool(n and n.absent),
                    'bareme': float(t.bareme),
                })
                continue
            sur20 = _to_float(n.sur_20)
            serie.append({
                'travail_id': t.id,
                'date': t.date_travail,
                'label': t.titre or t.get_type_travail_display(),
                'matiere': t.matiere.libelle,
                'note': _to_float(n.note),
                'sur_20': sur20,
                'absent': False,
                'bareme': float(t.bareme),
            })
            if sur20 is not None:
                points_moy.append((sur20, t.coefficient))

        notes_valides = [p['sur_20'] for p in serie if p['sur_20'] is not None]
        tendance, delta = _tendance(notes_valides)
        eleves.append({
            'inscription': ins,
            'eleve': ins.eleve,
            'serie': serie,
            'moyenne': _moyenne_ponderee(points_moy),
            'nb_notes': len(notes_valides),
            'derniere': notes_valides[-1] if notes_valides else None,
            'tendance': tendance,
            'delta': delta,
            'chart_labels': [
                f"{p['date'].strftime('%d/%m') if p['date'] else ''} {p['label']}"[:28]
                for p in serie
                if p['sur_20'] is not None
            ],
            'chart_values': [p['sur_20'] for p in serie if p['sur_20'] is not None],
        })

    # Moyenne de classe par travail (pour courbe de référence)
    classe_par_travail = []
    for t in travaux:
        vals = []
        for ins in inscriptions:
            n = notes_map.get(ins.id, {}).get(t.id)
            if n and not n.absent and n.sur_20 is not None:
                vals.append(float(n.sur_20))
        classe_par_travail.append({
            'travail_id': t.id,
            'label': f"{t.date_travail.strftime('%d/%m') if t.date_travail else ''} "
            f"{(t.titre or t.get_type_travail_display())}"[:28],
            'moyenne': round(sum(vals) / len(vals), 2) if vals else None,
        })

    return {
        'travaux': travaux,
        'eleves': eleves,
        'matieres': _matieres_cours(personnel, classe),
        'classe_par_travail': classe_par_travail,
        'moyenne_classe': (
            round(
                sum(e['moyenne'] for e in eleves if e['moyenne'] is not None)
                / max(1, sum(1 for e in eleves if e['moyenne'] is not None)),
                2,
            )
            if any(e['moyenne'] is not None for e in eleves)
            else None
        ),
        'nb_en_hausse': sum(1 for e in eleves if e['tendance'] == 'hausse'),
        'nb_en_baisse': sum(1 for e in eleves if e['tendance'] == 'baisse'),
    }


@login_required
def evolution_classe(request, pk):
    """Évolution des notes des élèves pour les cours du professeur dans la classe."""
    if not request.user.is_professeur:
        return redirect('utilisateur:post_login')

    personnel = _personnel(request.user)
    if not personnel:
        messages.warning(request, "Aucune fiche personnel n'est rattachée à votre compte.")
        return redirect('utilisateur:enseignant_dashboard')

    classe = get_object_or_404(
        Classe.objects.select_related('section', 'section__cycle', 'ecole', 'titulaire'),
        pk=pk,
        ecole=personnel.ecole,
    )
    if not _peut_voir_classe(personnel, classe):
        messages.error(request, "Vous n'avez pas accès à cette classe.")
        return redirect('utilisateur:enseignant_dashboard')

    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    if not annee:
        messages.warning(request, "Aucune année scolaire en cours.")
        return redirect('utilisateur:enseignant_classe', pk=classe.id)

    matieres = _matieres_cours(personnel, classe)
    if not matieres:
        messages.warning(
            request,
            "Aucune matière de cours ne vous est affectée dans cette classe.",
        )
        return redirect('utilisateur:enseignant_classe', pk=classe.id)

    matiere = None
    matiere_id = request.GET.get('matiere')
    if matiere_id:
        matiere = next((m for m in matieres if str(m.id) == str(matiere_id)), None)

    data = _construire_evolution(personnel, classe, annee, matiere=matiere)

    eleve_sel = None
    eleve_id = request.GET.get('eleve')
    if eleve_id:
        eleve_sel = next(
            (e for e in data['eleves'] if str(e['inscription'].id) == str(eleve_id)),
            None,
        )
    if eleve_sel is None and data['eleves']:
        # Premier élève ayant des notes, sinon le premier
        eleve_sel = next(
            (e for e in data['eleves'] if e['nb_notes'] > 0),
            data['eleves'][0],
        )

    return render(request, 'utilisateur/evolution_classe.html', {
        'personnel': personnel,
        'classe': classe,
        'annee_courante': annee,
        'matieres': data['matieres'],
        'matiere_filtre': matiere,
        'travaux': data['travaux'],
        'eleves': data['eleves'],
        'eleve_sel': eleve_sel,
        'classe_par_travail': data['classe_par_travail'],
        'moyenne_classe': data['moyenne_classe'],
        'nb_en_hausse': data['nb_en_hausse'],
        'nb_en_baisse': data['nb_en_baisse'],
        'nb_travaux': len(data['travaux']),
    })
