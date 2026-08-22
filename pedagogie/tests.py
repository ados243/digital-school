from datetime import date, timedelta

import jwt
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from common.tests_helpers import faire_annee, faire_classe, faire_ecole, faire_user
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from grh.models import Personnel
from pedagogie.models import CoursEnDirect, Matiere


class CalendrierNationalTests(TestCase):
    def setUp(self):
        self.ecole = faire_ecole()
        faire_annee()
        self.directeur = faire_user(self.ecole, "dir1", "DIRECTEUR")
        self.manager = faire_user(self.ecole, "man1", "MANAGER")
        self.manager.is_superuser = True
        self.manager.save()

    def test_directeur_ne_peut_pas_synchroniser(self):
        self.client.force_login(self.directeur)
        url = reverse("pedagogie:periodes_bulletin")
        response = self.client.post(url, {"action": "sync"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "administrateur plateforme")

    def test_emploi_du_temps_accessible(self):
        self.client.force_login(self.directeur)
        response = self.client.get(reverse("pedagogie:emploi_du_temps"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emploi du temps")


class CoursEnDirectJitsiTests(TestCase):
    def setUp(self):
        self.ecole = faire_ecole("VIS01", "École Visio")
        self.annee = faire_annee("2026-2027")
        self.classe = faire_classe(self.ecole, "6e A")
        self.enseignant = Personnel.objects.create(
            ecole=self.ecole,
            nom="Kanku",
            Post_nom="M",
            prenom="Sarah",
            sexe="Feminin",
            date_de_naissance=date(1990, 5, 12),
            nationalite="Congolaise",
            quartier=self.ecole.quartier,
            adresse="1 avenue Test",
            matricule="PER-VIS01",
            telephone="243810000000",
            fonction="Enseignant",
        )
        self.matiere = Matiere.objects.create(
            ecole=self.ecole,
            code="MATH6",
            libelle="Mathématiques",
            coefficient=4,
            maxima_periode=10,
            section=self.classe.section,
            enserignant=self.enseignant,
        )
        self.seance = CoursEnDirect.objects.create(
            ecole=self.ecole,
            annee_scolaire=self.annee,
            classe=self.classe,
            matiere=self.matiere,
            enseignant=self.enseignant,
            titre="Fractions et proportions",
            description="Séance de pratique guidée",
            date_heure_prevue=timezone.now() + timedelta(days=1),
            duree_minutes=60,
        )
        self.seance.classes.add(self.classe)

    @override_settings(JITSI_DOMAIN="https://meet.ecole.test")
    def test_jitsi_embed_url_adapte_selon_le_role(self):
        url_enseignant = self.seance.jitsi_embed_url("Mme Sarah", est_enseignant=True)
        url_eleve = self.seance.jitsi_embed_url("Amina", est_enseignant=False)

        self.assertIn("https://meet.ecole.test/", url_enseignant)
        self.assertIn("userInfo.displayName=Mme%20Sarah", url_enseignant)
        self.assertIn("config.startWithVideoMuted=false", url_enseignant)
        self.assertIn("config.startWithVideoMuted=true", url_eleve)
        self.assertIn("config.prejoinConfig.enabled=false", url_enseignant)
        self.assertIn("config.disableDeepLinking=true", url_enseignant)
        self.assertIn("config.resolution=720", url_enseignant)

    @override_settings(
        JITSI_PROVIDER="jaas",
        JITSI_DOMAIN="8x8.vc",
        JITSI_JAAS_APP_ID="vpaas-magic-cookie-testapp",
        JITSI_JAAS_API_KEY="test-key-id",
        JITSI_JAAS_JWT_TTL_SECONDS=3600,
    )
    def test_jitsi_embed_url_jaas_inclut_tenant_et_jwt(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        with self.settings(JITSI_JAAS_PRIVATE_KEY=pem):
            url = self.seance.jitsi_embed_url(
                "Mme Sarah",
                email="sarah@ecole.test",
                est_enseignant=True,
            )

        self.assertIn("https://8x8.vc/vpaas-magic-cookie-testapp/", url)
        self.assertIn("userInfo.displayName=Mme%20Sarah", url)
        self.assertIn("jwt=", url)

        token = url.split("jwt=", 1)[1].split("&", 1)[0]
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})

        self.assertEqual(header["kid"], "vpaas-magic-cookie-testapp/test-key-id")
        self.assertEqual(payload["sub"], "vpaas-magic-cookie-testapp")
        self.assertTrue(payload["context"]["user"]["moderator"])
        self.assertEqual(payload["context"]["user"]["email"], "sarah@ecole.test")
