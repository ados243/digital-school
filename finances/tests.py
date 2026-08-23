from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from common.tests_helpers import faire_annee, faire_classe, faire_ecole, faire_eleve, faire_tuteur, faire_user
from inscription.models import Inscription
from finances.models import Devise, Frais_Scolaire, Paiement, TypeFrais
from finances.paiement_utils import (
    code_rubrique_pour_type_frais,
    frais_concerne_inscription,
    frais_disponibles_pour_inscription,
    realisations_budget,
)


class WebhookMobileMoneyTests(TestCase):
    @override_settings(MOBILE_MONEY_WEBHOOK_TOKEN="secret-test")
    def test_webhook_refuse_sans_token(self):
        response = self.client.post("/webhooks/mobile-money/", {"reference": "MM-X"})
        self.assertEqual(response.status_code, 403)

    @override_settings(MOBILE_MONEY_WEBHOOK_TOKEN="secret-test")
    def test_webhook_reference_inconnue(self):
        response = self.client.post(
            "/webhooks/mobile-money/?token=secret-test",
            {"reference": "MM-INCONNUE"},
        )
        self.assertEqual(response.status_code, 404)


class RelancesImpayesTests(TestCase):
    def setUp(self):
        self.ecole = faire_ecole()
        self.directeur = faire_user(self.ecole, "dir_fin", "DIRECTEUR")

    def test_page_relances_accessible(self):
        self.client.force_login(self.directeur)
        response = self.client.get(reverse("finances:relances_impayes"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relances minerval")

    def test_envoi_sans_whatsapp_actif(self):
        self.client.force_login(self.directeur)
        response = self.client.post(reverse("finances:relances_impayes_envoyer"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WhatsApp")


class AccesFinancesTests(TestCase):
    def setUp(self):
        self.ecole = faire_ecole()
        self.caissier = faire_user(self.ecole, "caisse1", "CAISSIER")

    def test_caissier_voit_liste_paiements(self):
        self.client.force_login(self.caissier)
        response = self.client.get(reverse("finances:paiement_list"))
        self.assertEqual(response.status_code, 200)


class MappingRubriqueBudgetTests(SimpleTestCase):
    def test_codes_selon_libelle(self):
        self.assertEqual(code_rubrique_pour_type_frais("Minerval"), "R_MINERVAL")
        self.assertEqual(code_rubrique_pour_type_frais("Frais de scolarité"), "R_MINERVAL")
        self.assertEqual(code_rubrique_pour_type_frais("Frais d'inscription"), "R_INSCRIPTION")
        self.assertEqual(code_rubrique_pour_type_frais("Tenue scolaire"), "R_TENUE")
        self.assertEqual(code_rubrique_pour_type_frais("Examen 1er trimestre"), "R_EXAMEN")
        self.assertEqual(code_rubrique_pour_type_frais("Divers"), "R_AUTRES")


class BudgetSuiviTests(TestCase):
    def setUp(self):
        self.ecole = faire_ecole()
        self.directeur = faire_user(self.ecole, "dir_budg", "DIRECTEUR")
        self.annee = faire_annee()
        self.classe = faire_classe(self.ecole)
        self.tuteur = faire_tuteur(self.ecole)
        self.eleve = faire_eleve(self.ecole, self.tuteur)
        self.devise = Devise.objects.create(devise="USD")
        self.type_minerval = TypeFrais.objects.create(
            ecole=self.ecole,
            libelle="Minerval",
            description="Frais scolaire",
        )
        self.frais = Frais_Scolaire.objects.create(
            type_frais=self.type_minerval,
            annee=self.annee,
            section=self.classe.section,
            montant=Decimal("100.00"),
            devise=self.devise,
            echeance=date(2025, 10, 1),
        )
        self.inscription = Inscription.objects.create(
            eleve=self.eleve,
            classe=self.classe,
            annee_s=self.annee,
        )

    def test_page_suivi_accessible(self):
        self.client.force_login(self.directeur)
        response = self.client.get(reverse("finances:budget_annuel"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suivi du budget")
        self.assertContains(response, "Exporter Excel")
        self.assertContains(response, "Suivi des recettes")

    def test_export_excel(self):
        self.client.force_login(self.directeur)
        response = self.client.get(reverse("finances:budget_annuel"), {"export": "excel"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn(".xlsx", response["Content-Disposition"])
        self.assertGreater(len(response.content), 100)

    def test_paiement_minerval_compte_dans_le_realise(self):
        Paiement.objects.create(
            eleve=self.inscription,
            frais=self.frais,
            numero_recu="R-BUDGET-1",
            montant_paye=Decimal("50.00"),
            devise=self.devise,
            mode_paiement="ESPECES",
            statut="VALIDE",
            caissier="caisse1",
        )
        reali = realisations_budget(self.ecole, self.annee)
        self.assertEqual(reali["R_MINERVAL"]["usd"], Decimal("50.00"))
        self.assertEqual(reali["R_MINERVAL"]["cdf"], Decimal("0"))

    def test_salaires_calcules_automatiquement_dans_depenses(self):
        from finances.paiement_utils import construire_postes_budget
        from grh.models import Contrat, Personnel

        personnel = Personnel.objects.create(
            ecole=self.ecole,
            nom="Kabongo",
            Post_nom="M",
            prenom="Paul",
            sexe="Masculin",
            date_de_naissance=date(1985, 1, 1),
            nationalite="Congolaise",
            quartier=self.ecole.quartier,
            adresse="1 av. Test",
            telephone="243811111199",
            fonction="Enseignant",
        )
        Contrat.objects.create(
            personnel=personnel,
            type_contrat="CDI",
            date_debut=date(2025, 9, 1),
            salaire_base=Decimal("200.00"),
            devise=self.devise,
            statut="ACTIF",
        )
        plan = construire_postes_budget(self.ecole, self.annee, budget=None)
        poste_sal = next(
            p for p in plan["depenses"] if p["rubrique"].code == "D_SALAIRES"
        )
        self.assertEqual(poste_sal["montant_usd"], Decimal("2400.00"))
        self.assertEqual(poste_sal["montant_cdf"], Decimal("0"))
        self.assertTrue(poste_sal["est_auto"])
        self.assertIn("1 contrat", poste_sal["note"])

    def test_frais_ajoutes_apres_fixation_entrent_dans_le_solde(self):
        from django.utils import timezone
        from finances.defaults import assurer_rubriques_budget
        from finances.models import BudgetAnnuel, PosteBudget, RubriqueBudget
        from finances.paiement_utils import construire_postes_budget

        assurer_rubriques_budget()
        rub_labo = RubriqueBudget.objects.get(code="R_LABO")
        budget = BudgetAnnuel.objects.create(
            ecole=self.ecole,
            annee=self.annee,
            date_fixation=timezone.now(),
            fixe_par="test",
        )
        PosteBudget.objects.create(
            budget=budget,
            rubrique=rub_labo,
            montant_usd=Decimal("0"),
            montant_cdf=Decimal("0"),
        )
        type_labo = TypeFrais.objects.create(
            ecole=self.ecole,
            libelle="Laboratoire",
            description="Frais labo",
        )
        Frais_Scolaire.objects.create(
            type_frais=type_labo,
            annee=self.annee,
            section=self.classe.section,
            montant=Decimal("25.00"),
            devise=self.devise,
            echeance=date(2025, 11, 1),
        )
        plan = construire_postes_budget(self.ecole, self.annee, budget=budget)
        poste_labo = next(p for p in plan["recettes"] if p["rubrique"].code == "R_LABO")
        # 40 places × 25 USD
        self.assertEqual(poste_labo["montant_usd"], Decimal("1000.00"))
        self.assertIn("après fixation", poste_labo["note"])
        self.assertGreater(plan["total_recettes_usd"], Decimal("0"))

    def test_charges_hoada_entrent_dans_le_realise(self):
        from finances.models import CompteComptable, Ecriture, EcritureLigne, JournalComptable
        from finances.paiement_utils import realisations_budget

        journal = JournalComptable.objects.create(
            ecole=self.ecole, code="OD", libelle="Opérations diverses"
        )
        compte = CompteComptable.objects.create(
            ecole=self.ecole,
            numero="604000",
            libelle="Fournitures pédagogiques",
            devise=self.devise,
        )
        ecriture = Ecriture.objects.create(
            ecole=self.ecole,
            date_ecriture=date(2025, 10, 15),
            journal=journal,
            libelle="Achat cahiers",
        )
        EcritureLigne.objects.create(
            ecriture=ecriture,
            compte=compte,
            sens="DEBIT",
            montant=Decimal("80.00"),
        )
        reali = realisations_budget(self.ecole, self.annee)
        self.assertEqual(reali["D_FOURNITURES"]["usd"], Decimal("80.00"))


class FraisParClasseTests(TestCase):
    def setUp(self):
        self.ecole = faire_ecole()
        self.annee = faire_annee()
        self.classe_a = faire_classe(self.ecole, nom="6A")
        self.classe_b = faire_classe(self.ecole, nom="6B")
        self.tuteur = faire_tuteur(self.ecole)
        self.eleve_a = faire_eleve(self.ecole, self.tuteur, prenom="Amina")
        self.eleve_b = faire_eleve(self.ecole, self.tuteur, prenom="Binta")
        self.devise = Devise.objects.create(devise="USD")
        self.type_labo = TypeFrais.objects.create(
            ecole=self.ecole,
            libelle="Laboratoire",
            description="Frais labo",
        )
        self.ins_a = Inscription.objects.create(
            eleve=self.eleve_a, classe=self.classe_a, annee_s=self.annee
        )
        self.ins_b = Inscription.objects.create(
            eleve=self.eleve_b, classe=self.classe_b, annee_s=self.annee
        )

    def test_frais_specifique_uniquement_classes_ciblees(self):
        frais = Frais_Scolaire.objects.create(
            type_frais=self.type_labo,
            annee=self.annee,
            section=None,
            montant=Decimal("25.00"),
            devise=self.devise,
            echeance=date(2025, 11, 1),
        )
        frais.classes.set([self.classe_a])

        self.assertTrue(frais.est_specifique())
        self.assertTrue(frais_concerne_inscription(frais, self.ins_a))
        self.assertFalse(frais_concerne_inscription(frais, self.ins_b))

        dus_a = [d["frais"].pk for d in frais_disponibles_pour_inscription(self.ecole, self.ins_a)]
        dus_b = [d["frais"].pk for d in frais_disponibles_pour_inscription(self.ecole, self.ins_b)]
        self.assertIn(frais.pk, dus_a)
        self.assertNotIn(frais.pk, dus_b)

    def test_formulaire_cree_frais_multi_classes(self):
        from finances.forms import FraisScolaireForm

        form = FraisScolaireForm(
            {
                "type_frais": self.type_labo.pk,
                "annee": self.annee.pk,
                "portee": "classes",
                "classes": [self.classe_a.pk, self.classe_b.pk],
                "montant": "40.00",
                "devise": self.devise.pk,
                "echeance": "2025-12-15",
                "est_obligatoire": "on",
            },
            ecole=self.ecole,
        )
        self.assertTrue(form.is_valid(), form.errors)
        frais = form.save()
        self.assertIsNone(frais.section_id)
        self.assertEqual(set(frais.classes.values_list("id", flat=True)), {self.classe_a.id, self.classe_b.id})
        self.assertTrue(frais_concerne_inscription(frais, self.ins_a))
        self.assertTrue(frais_concerne_inscription(frais, self.ins_b))


class CaisseDisponibleTests(TestCase):
    def setUp(self):
        self.ecole = faire_ecole()
        self.devise = Devise.objects.create(devise="USD")
        self.annee = faire_annee()
        self.classe = faire_classe(self.ecole)
        self.tuteur = faire_tuteur(self.ecole)
        self.eleve = faire_eleve(self.ecole, self.tuteur)
        self.inscription = Inscription.objects.create(
            eleve=self.eleve,
            classe=self.classe,
            annee_s=self.annee,
        )
        self.type_frais = TypeFrais.objects.create(
            ecole=self.ecole, libelle="Minerval", description=""
        )
        self.frais = Frais_Scolaire.objects.create(
            type_frais=self.type_frais,
            annee=self.annee,
            section=self.classe.section,
            montant=Decimal("100.00"),
            devise=self.devise,
            echeance=date(2026, 12, 31),
            est_obligatoire=True,
        )

    def test_refuse_depense_sans_fonds(self):
        from finances.paiement_utils import verifier_depense_contre_caisse

        ok, msg, dispo = verifier_depense_contre_caisse(
            self.ecole, Decimal("50"), "USD", "ESPECES"
        )
        self.assertFalse(ok)
        self.assertIn("Dépense impossible", msg)
        self.assertEqual(dispo, Decimal("0"))

    def test_autorise_depense_avec_fonds(self):
        from finances.paiement_utils import verifier_depense_contre_caisse

        Paiement.objects.create(
            eleve=self.inscription,
            frais=self.frais,
            numero_recu="TEST-CAISSE-1",
            montant_paye=Decimal("200.00"),
            devise=self.devise,
            mode_paiement="ESPECES",
            caissier="test",
            statut="VALIDE",
        )
        ok, msg, dispo = verifier_depense_contre_caisse(
            self.ecole, Decimal("50"), "USD", "ESPECES"
        )
        self.assertTrue(ok)
        self.assertEqual(msg, "")
        self.assertEqual(dispo, Decimal("200.00"))

