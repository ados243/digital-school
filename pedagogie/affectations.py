"""Helpers d'affectation enseignant ↔ matière ↔ classe (RDC / primaire)."""

from django.db.models import Q

from inscription.models import Classe
from pedagogie.models import AffectationEnseignement, Matiere


CYCLES_TITULAIRE_DEFAUT = frozenset({'PRIMAIRE', 'MATERNELLE'})


def cycle_utilise_titulaire_par_defaut(classe_ou_cycle):
    if hasattr(classe_ou_cycle, 'section'):
        cycle = getattr(getattr(classe_ou_cycle.section, 'cycle', None), 'cycle', '') or ''
    else:
        cycle = classe_ou_cycle or ''
    return cycle in CYCLES_TITULAIRE_DEFAUT


def est_titulaire_classe(personnel, classe):
    """True si le personnel est le professeur titulaire de la classe."""
    if not personnel or not classe:
        return False
    return bool(classe.titulaire_id and classe.titulaire_id == personnel.id)


def enseignant_effectif(matiere, classe):
    """Retourne le professeur qui assure la matière dans la classe."""
    return matiere.enseignant_pour_classe(classe)


def matieres_avec_enseignant(classe):
    """Liste des matières de la section avec enseignant effectif + source."""
    matieres = (
        Matiere.objects.filter(ecole=classe.ecole, section=classe.section)
        .select_related('enserignant', 'section', 'section__cycle')
        .order_by('libelle')
    )
    affectations = {
        a.matiere_id: a
        for a in AffectationEnseignement.objects.filter(classe=classe).select_related('enseignant')
    }
    rows = []
    titulaire_defaut = cycle_utilise_titulaire_par_defaut(classe)
    for m in matieres:
        aff = affectations.get(m.id)
        if aff:
            rows.append({
                'matiere': m,
                'enseignant': aff.enseignant,
                'source': 'affectation',
                'affectation': aff,
                'libelle_source': 'Affectation spécifique',
            })
        elif titulaire_defaut and classe.titulaire_id:
            rows.append({
                'matiere': m,
                'enseignant': classe.titulaire,
                'source': 'titulaire',
                'affectation': None,
                'libelle_source': 'Titulaire de classe (défaut)',
            })
        else:
            rows.append({
                'matiere': m,
                'enseignant': m.enserignant,
                'source': 'reference',
                'affectation': None,
                'libelle_source': 'Enseignant de référence',
            })
    return rows


def classes_et_matieres_enseignant(personnel):
    """Classes / matières accessibles à un enseignant (titulaire ou affecté)."""
    ecole = personnel.ecole
    classes_titulaire = Classe.objects.filter(
        ecole=ecole, titulaire=personnel
    ).select_related('section', 'section__cycle')

    affectations = (
        AffectationEnseignement.objects.filter(enseignant=personnel, ecole=ecole)
        .select_related('classe', 'classe__section', 'matiere')
    )

    # Matières de référence (secondaire / humanités)
    matieres_ref = Matiere.objects.filter(ecole=ecole, enserignant=personnel)

    return {
        'classes_titulaire': classes_titulaire,
        'affectations': affectations,
        'matieres_reference': matieres_ref,
    }


def peut_gerer_matiere_classe(personnel, matiere, classe):
    """Droit de saisir notes / travaux pour cette matière dans cette classe."""
    if not personnel:
        return False
    if classe.titulaire_id == personnel.id:
        # Titulaire : toutes les matières sauf celles affectées à un autre
        aff = AffectationEnseignement.objects.filter(classe=classe, matiere=matiere).first()
        if aff and aff.enseignant_id != personnel.id:
            return False
        return True
    effectif = enseignant_effectif(matiere, classe)
    return bool(effectif and effectif.id == personnel.id)


def travaux_accessibles_qs(personnel, base_qs):
    """Filtre les travaux cotés visibles / gérables par l'enseignant."""
    ecole = personnel.ecole
    classe_ids_titulaire = list(
        Classe.objects.filter(ecole=ecole, titulaire=personnel).values_list('id', flat=True)
    )
    aff_mine = list(
        AffectationEnseignement.objects.filter(
            enseignant=personnel, ecole=ecole
        ).values_list('classe_id', 'matiere_id')
    )
    # Cours confiés à un autre prof : exclus même pour le titulaire / la référence
    aff_autres = list(
        AffectationEnseignement.objects.filter(ecole=ecole)
        .exclude(enseignant=personnel)
        .values_list('classe_id', 'matiere_id')
    )

    q = Q(matiere__enserignant=personnel)
    if classe_ids_titulaire:
        q |= Q(classe_id__in=classe_ids_titulaire)
    for classe_id, matiere_id in aff_mine:
        q |= Q(classe_id=classe_id, matiere_id=matiere_id)

    qs = base_qs.filter(q)
    for classe_id, matiere_id in aff_autres:
        qs = qs.exclude(classe_id=classe_id, matiere_id=matiere_id)
    return qs.distinct()
