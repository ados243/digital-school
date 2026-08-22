"""Données minimales pour les tests multi-école."""

from datetime import date

from inscription.models import Annee_Scolaire, Classe, Commune, Cycle, Ecole, Eleve, Quartier, Section, Tuteur
from utilisateur.models import Utilisateur


def faire_ecole(code="TST01", nom="École Test"):
    commune = Commune.objects.create(commune=f"Commune {code}")
    quartier = Quartier.objects.create(commune=commune, quartier=f"Quartier {code}")
    return Ecole.objects.create(
        code_ecole=code,
        ecole=nom,
        quartier=quartier,
        adresse="1 av. Test",
        telephone1="243800000001",
        telephone2="243800000002",
        email=f"{code.lower()}@test.cd",
        activation=True,
    )


def faire_annee(libelle="2025-2026"):
    return Annee_Scolaire.objects.create(
        anne_scolaire=libelle,
        date_debut=date(2025, 9, 1),
        date_fin=date(2026, 7, 15),
        est_encoure=True,
    )


def faire_classe(ecole, nom="6A"):
    cycle, _ = Cycle.objects.get_or_create(cycle="PRIMAIRE")
    section, _ = Section.objects.get_or_create(
        section="Primaire",
        defaults={"cycle": cycle},
    )
    if section.cycle_id != cycle.id:
        section.cycle = cycle
        section.save(update_fields=["cycle"])
    return Classe.objects.create(
        ecole=ecole,
        section=section,
        classe=nom,
        capacite_max=40,
        salle="S1",
    )


def faire_tuteur(ecole, nom="Mbala", prenom="Jean", telephone="243811111111"):
    return Tuteur.objects.create(
        ecole=ecole,
        nom=nom,
        Post_nom="N",
        prenom=prenom,
        telephone=telephone,
        email=f"{prenom.lower()}@famille.cd",
    )


def faire_eleve(ecole, tuteur, nom="Mbala", prenom="Amina"):
    return Eleve.objects.create(
        ecole=ecole,
        nom=nom,
        Post_nom="K",
        prenom=prenom,
        titeur=tuteur,
        sexe="Feminin",
        date_de_naissance=date(2014, 5, 1),
    )


def faire_user(ecole, username, role, password="MotDePasseFort12", **kwargs):
    return Utilisateur.objects.create_user(
        username=username,
        password=password,
        prenom=username,
        last_name="Test",
        role=role,
        ecole=ecole,
        **kwargs,
    )
