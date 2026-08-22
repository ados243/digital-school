from django.test import TestCase, override_settings
from django.urls import reverse

from common.tests_helpers import faire_ecole, faire_user


class SeedGrhTests(TestCase):
    def setUp(self):
        self.ecole = faire_ecole()
        self.staff = faire_user(self.ecole, "directeur1", "DIRECTEUR")
        self.admin = faire_user(self.ecole, "super1", "MANAGER")
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save()

    @override_settings(DEBUG=True)
    def test_seed_demo_interdit_non_superuser(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("grh:generer_demo"))
        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=False)
    def test_seed_demo_interdit_hors_debug(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("grh:generer_demo"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "développement")
