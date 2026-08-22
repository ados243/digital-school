"""Types de frais et rubriques budgétaires créés par défaut."""

TYPE_FRAIS_SYSTEME = (
    {
        "libelle": "Minerval",
        "description": "Frais scolaire",
    },
)

# Plan type d'un budget scolaire (RDC) — recettes puis dépenses.
RUBRIQUES_BUDGET_SYSTEME = (
    # ——— Recettes ———
    {
        "code": "R_MINERVAL",
        "libelle": "Minerval / frais de scolarité",
        "nature": "RECETTE",
        "ordre": 10,
        "calcul_auto": "MINERVAL",
        "description": "Capacité des classes × barème minerval",
    },
    {
        "code": "R_INSCRIPTION",
        "libelle": "Frais d'inscription",
        "nature": "RECETTE",
        "ordre": 20,
        "calcul_auto": "INSCRIPTION",
        "description": "Capacité × frais d'inscription par section",
    },
    {
        "code": "R_EXAMEN",
        "libelle": "Frais d'examen / compositions",
        "nature": "RECETTE",
        "ordre": 30,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "R_TENUE",
        "libelle": "Tenues / uniformes",
        "nature": "RECETTE",
        "ordre": 40,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "R_LABO",
        "libelle": "Laboratoire / informatique",
        "nature": "RECETTE",
        "ordre": 50,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "R_TRANSPORT",
        "libelle": "Transport scolaire",
        "nature": "RECETTE",
        "ordre": 60,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "R_CANTINE",
        "libelle": "Cantine / restauration",
        "nature": "RECETTE",
        "ordre": 70,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "R_COTI",
        "libelle": "Cotisations / association des parents",
        "nature": "RECETTE",
        "ordre": 80,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "R_SUBVENTION",
        "libelle": "Subventions / dons",
        "nature": "RECETTE",
        "ordre": 90,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "R_AUTRES",
        "libelle": "Autres recettes",
        "nature": "RECETTE",
        "ordre": 100,
        "calcul_auto": "",
        "description": "",
    },
    # ——— Dépenses ———
    {
        "code": "D_SALAIRES",
        "libelle": "Salaires du personnel",
        "nature": "DEPENSE",
        "ordre": 10,
        "calcul_auto": "SALAIRES",
        "description": "Somme des salaires de base des contrats actifs (en vigueur sur l'année) × 12 mois",
    },
    {
        "code": "D_CHARGES_SOC",
        "libelle": "Charges sociales (INSS / ONEM)",
        "nature": "DEPENSE",
        "ordre": 20,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_FOURNITURES",
        "libelle": "Fournitures pédagogiques",
        "nature": "DEPENSE",
        "ordre": 30,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_DIDACTIQUE",
        "libelle": "Matériel didactique / manuels",
        "nature": "DEPENSE",
        "ordre": 40,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_EAU_ELEC",
        "libelle": "Eau et électricité",
        "nature": "DEPENSE",
        "ordre": 50,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_INTERNET",
        "libelle": "Internet / télécommunications",
        "nature": "DEPENSE",
        "ordre": 60,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_ENTRETIEN",
        "libelle": "Entretien et maintenance",
        "nature": "DEPENSE",
        "ordre": 70,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_CARBURANT",
        "libelle": "Carburant / transport",
        "nature": "DEPENSE",
        "ordre": 80,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_SECURITE",
        "libelle": "Sécurité / gardiennage",
        "nature": "DEPENSE",
        "ordre": 90,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_IMPOTS",
        "libelle": "Impôts et taxes",
        "nature": "DEPENSE",
        "ordre": 100,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_ASSURANCE",
        "libelle": "Assurances",
        "nature": "DEPENSE",
        "ordre": 110,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_FORMATION",
        "libelle": "Formation / recyclage",
        "nature": "DEPENSE",
        "ordre": 120,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_INVEST",
        "libelle": "Investissements / équipements",
        "nature": "DEPENSE",
        "ordre": 130,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_PARASCO",
        "libelle": "Activités parascolaires",
        "nature": "DEPENSE",
        "ordre": 140,
        "calcul_auto": "",
        "description": "",
    },
    {
        "code": "D_IMPREVUS",
        "libelle": "Imprévus / divers",
        "nature": "DEPENSE",
        "ordre": 150,
        "calcul_auto": "",
        "description": "",
    },
)


def assurer_types_frais_systeme(ecole):
    """Crée les types de frais système manquants pour une école (idempotent)."""
    if ecole is None:
        return []
    from .models import TypeFrais

    created = []
    for spec in TYPE_FRAIS_SYSTEME:
        obj, was_created = TypeFrais.objects.get_or_create(
            ecole=ecole,
            libelle=spec["libelle"],
            defaults={"description": spec["description"]},
        )
        if was_created:
            created.append(obj)
    return created


def assurer_rubriques_budget():
    """Crée / met à jour le catalogue des rubriques budgétaires (idempotent)."""
    from .models import RubriqueBudget

    created = []
    for spec in RUBRIQUES_BUDGET_SYSTEME:
        obj, was_created = RubriqueBudget.objects.update_or_create(
            code=spec["code"],
            defaults={
                "libelle": spec["libelle"],
                "nature": spec["nature"],
                "ordre": spec["ordre"],
                "calcul_auto": spec.get("calcul_auto") or "",
                "description": spec.get("description") or "",
                "actif": True,
            },
        )
        if was_created:
            created.append(obj)
    return created
