"""Calendrier scolaire national RDC (MINEDU-NC / EPSP).

Référence : calendrier officiel 2025-2026
(rentrée 1er septembre → clôture 2 juillet, 222 jours de classe).

- Maternelle & Primaire : 3 trimestres × 2 périodes bulletin
- CTEB (Secondaire) & Humanités : 2 semestres × 2 périodes bulletin

Les dates des périodes (TJ) sont calées sur les congés de détente et
vacances publiés (Noël, Pâques).
"""

from datetime import date

# Structure relative à (y0, y1) = années civiles du libellé YYYY-YYYY.
# Tuple date : (mois, jour, offset) avec offset 0 = y0, 1 = y1.
#
# Source MINEDU-NC 2025-2026 :
# - Année : 01/09/2025 → 02/07/2026
# - Trim.1 : 01/09 → 17/12/2025 | détente 30/10–01/11
# - Trim.2 : 05/01 → 27/03/2026 | détente 12–14/02 | Pâques 28/03–11/04
# - Trim.3 : 13/04 → 02/07/2026
# - Sem.1  : 01/09/2025 → 11/02/2026
# - Sem.2  : 16/02 → 02/07/2026

DATE_RENTREE = (9, 1, 0)
DATE_CLOTURE = (7, 2, 1)

STRUCTURE_TRIMESTRIELLE = [
    (
        1,
        (9, 1, 0),
        (12, 17, 0),
        [
            (1, (9, 1, 0), (10, 29, 0)),
            (2, (11, 3, 0), (12, 17, 0)),
        ],
    ),
    (
        2,
        (1, 5, 1),
        (3, 27, 1),
        [
            (3, (1, 5, 1), (2, 11, 1)),
            (4, (2, 16, 1), (3, 27, 1)),
        ],
    ),
    (
        3,
        (4, 13, 1),
        (7, 2, 1),
        [
            (5, (4, 13, 1), (5, 29, 1)),
            (6, (6, 1, 1), (7, 2, 1)),
        ],
    ),
]

STRUCTURE_SEMESTRIELLE = [
    (
        1,
        (9, 1, 0),
        (2, 11, 1),
        [
            (1, (9, 1, 0), (10, 29, 0)),
            (2, (11, 3, 0), (2, 11, 1)),
        ],
    ),
    (
        2,
        (2, 16, 1),
        (7, 2, 1),
        [
            (3, (2, 16, 1), (3, 27, 1)),
            (4, (4, 13, 1), (7, 2, 1)),
        ],
    ),
]

MODE_PAR_CYCLE = {
    'MATERNELLE': ('TRIMESTRE', STRUCTURE_TRIMESTRIELLE),
    'PRIMAIRE': ('TRIMESTRE', STRUCTURE_TRIMESTRIELLE),
    'SECONDAIRE': ('SEMESTRE', STRUCTURE_SEMESTRIELLE),
    'HUMANITE': ('SEMESTRE', STRUCTURE_SEMESTRIELLE),
}


def annees_civiles_depuis_libelle(libelle, date_debut=None, date_fin=None):
    parts = (libelle or '').split('-')
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return int(parts[0]), int(parts[1])
    if date_debut and date_fin:
        return date_debut.year, date_fin.year
    raise ValueError(f'Libellé année scolaire invalide : {libelle!r}')


def resolve_date(y0, y1, mois, jour, offset):
    return date(y0 if offset == 0 else y1, mois, jour)


def dates_annee_nationale(y0, y1):
    return (
        resolve_date(y0, y1, *DATE_RENTREE),
        resolve_date(y0, y1, *DATE_CLOTURE),
    )


def ordinal_periode(n):
    return {
        1: '1ère Période',
        2: '2ème Période',
        3: '3ème Période',
        4: '4ème Période',
        5: '5ème Période',
        6: '6ème Période',
    }.get(n, f'{n}ème Période')


def ordinal_trimestre(n):
    return {1: '1er Trimestre', 2: '2ème Trimestre', 3: '3ème Trimestre'}.get(
        n, f'{n}ème Trimestre'
    )


def ordinal_semestre(n):
    return {1: '1er Semestre', 2: '2ème Semestre'}.get(n, f'{n}ème Semestre')
