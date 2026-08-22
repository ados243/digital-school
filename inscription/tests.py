from django.test import TestCase, override_settings
from django.urls import reverse

from common.tests_helpers import faire_ecole, faire_tuteur, faire_user
from common.tenant import get_user_ecole


class TenantInscriptionTests(TestCase):
    def setUp(self):
        self.ecole_a = faire_ecole("ECA01", "École A")
        self.ecole_b = faire_ecole("ECB01", "École B")
        self.tuteur_a = faire_tuteur(self.ecole_a, nom="Alpha", prenom="ParentA")
        self.tuteur_b = faire_tuteur(self.ecole_b, nom="Beta", prenom="ParentB", telephone="243822222222")
        self.staff_a = faire_user(self.ecole_a, "secretaire_a", "DIRECTEUR")
        self.staff_b = faire_user(self.ecole_b, "secretaire_b", "DIRECTEUR")

    def test_liste_tuteurs_isolee_par_ecole(self):
        self.client.force_login(self.staff_a)
        response = self.client.get(reverse("inscription:tuteur_list"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("ParentA", html)
        self.assertNotIn("ParentB", html)

    def test_fiche_tuteur_autre_ecole_404(self):
        self.client.force_login(self.staff_a)
        url = reverse("inscription:tuteur_update", args=[self.tuteur_b.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_user_ecole(self):
        class Req:
            user = self.staff_a
        self.assertEqual(get_user_ecole(Req()), self.ecole_a)
