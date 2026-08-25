from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from inscription.models import Commune, Ecole, Eleve, Quartier, Tuteur
from utilisateur.models import JournalAcces, SessionConnexion, Utilisateur, VerrouillageConnexion
from utilisateur.security import MSG_AUTH_GENERIQUE


def _ecole():
    commune = Commune.objects.create(commune="Gombe")
    quartier = Quartier.objects.create(commune=commune, quartier="Centre")
    return Ecole.objects.create(
        code_ecole="TST01",
        ecole="École Test",
        quartier=quartier,
        adresse="1 av. Test",
        telephone1="243800000001",
        telephone2="243800000002",
        email="ecole@test.cd",
        activation=True,
    )


class SecuriteAccessibiliteTests(TestCase):
    def setUp(self):
        self.ecole = _ecole()
        self.tuteur = Tuteur.objects.create(
            ecole=self.ecole,
            nom="Mbala",
            Post_nom="N",
            prenom="Jean",
            telephone="243811111111",
            email="parent@famille.cd",
        )
        self.eleve = Eleve.objects.create(
            ecole=self.ecole,
            nom="Mbala",
            Post_nom="K",
            prenom="Amina",
            titeur=self.tuteur,
            sexe="Feminin",
            date_de_naissance=date(2014, 5, 1),
        )
        self.parent = Utilisateur.objects.create_user(
            username="parent1",
            password="MotDePasseFort12",
            prenom="Jean",
            last_name="Mbala",
            role="PARENT",
            ecole=self.ecole,
            tuteur=self.tuteur,
            email="parent@famille.cd",
        )
        self.autre_tuteur = Tuteur.objects.create(
            ecole=self.ecole,
            nom="Kanda",
            Post_nom="P",
            prenom="Luc",
            telephone="243822222222",
            email="autre@famille.cd",
        )
        self.autre_eleve = Eleve.objects.create(
            ecole=self.ecole,
            nom="Kanda",
            Post_nom="M",
            prenom="Léa",
            titeur=self.autre_tuteur,
            sexe="Feminin",
            date_de_naissance=date(2013, 3, 12),
        )

    def test_pages_publiques_lang_fr_et_labels(self):
        for url_name in (
            "utilisateur:login",
            "utilisateur:inscription",
            "utilisateur:password_reset",
        ):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()
            self.assertIn('<html lang="fr">', html)
            self.assertIn('skip-link', html)
            self.assertIn('Aller au contenu principal', html)

    def test_connexion_message_generique(self):
        response = self.client.post(reverse("utilisateur:login"), {
            "username": "inconnu",
            "password": "mauvais",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, MSG_AUTH_GENERIQUE)
        self.assertNotContains(response, "n'existe pas")

    @override_settings(LOGIN_LOCKOUT_LIMIT=3, LOGIN_LOCKOUT_MINUTES=15)
    def test_verrouillage_apres_echecs(self):
        url = reverse("utilisateur:login")
        for _ in range(3):
            self.client.post(url, {"username": "parent1", "password": "wrongwrong12"})
        self.assertTrue(VerrouillageConnexion.objects.filter(echecs__gte=3).exists())
        # Mot de passe correct : toujours refusé tant que verrouillé
        response = self.client.post(url, {
            "username": "parent1",
            "password": "MotDePasseFort12",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, MSG_AUTH_GENERIQUE)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_idor_parent_ne_voit_pas_enfant_d_autrui(self):
        self.client.force_login(self.parent)
        url = reverse("utilisateur:parent_enfant", args=[self.autre_eleve.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_parent_voit_son_enfant_et_journalise(self):
        self.client.force_login(self.parent)
        url = reverse("utilisateur:parent_enfant", args=[self.eleve.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            JournalAcces.objects.filter(
                utilisateur=self.parent,
                action="CONSULTATION_ELEVE",
                identifiant=str(self.eleve.pk),
            ).exists()
        )

    def test_eleve_bloque_finances(self):
        eleve_user = Utilisateur.objects.create_user(
            username="eleve1",
            password="MotDePasseFort12",
            prenom="Amina",
            role="ELEVE",
            ecole=self.ecole,
            eleve=self.eleve,
        )
        self.client.force_login(eleve_user)
        response = self.client.get("/finances/", follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/mon-espace", response.url)

    def test_eleve_bloque_espace_enseignant(self):
        eleve_user = Utilisateur.objects.create_user(
            username="eleve2",
            password="MotDePasseFort12",
            prenom="Amina",
            role="ELEVE",
            ecole=self.ecole,
            eleve=self.eleve,
        )
        self.client.force_login(eleve_user)
        response = self.client.get(reverse("utilisateur:enseignant_dashboard"), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("utilisateur:portail"))

    def test_inscription_matricule_invalide_message_generique(self):
        response = self.client.post(reverse("utilisateur:inscription"), {
            "profil": "PARENT",
            "matricule": "XXXX-999",
            "nom": "Inconnu",
            "prenom": "Test",
            "username": "nouveaucompte",
            "password1": "MotDePasseFort12",
            "password2": "MotDePasseFort12",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ne correspondent pas")

    def test_anonymiser_eleve(self):
        eleve_user = Utilisateur.objects.create_user(
            username="eleve3",
            password="MotDePasseFort12",
            prenom="Amina",
            role="ELEVE",
            ecole=self.ecole,
            eleve=self.eleve,
            email="amina@test.cd",
        )
        self.eleve.anonymiser()
        self.eleve.refresh_from_db()
        eleve_user.refresh_from_db()
        self.assertEqual(self.eleve.nom, "Anonymisé")
        self.assertFalse(eleve_user.is_active)
        self.assertEqual(eleve_user.email, "")

    @override_settings(INSCRIPTION_WHATSAPP_ACTIF=True)
    @patch("utilisateur.auth_views.envoyer_code_whatsapp", return_value=(True, ""))
    def test_inscription_envoie_code_vers_whatsapp_ecole(self, mock_otp):
        response = self.client.post(reverse("utilisateur:inscription"), {
            "profil": "PARENT",
            "matricule": self.autre_tuteur.matricule,
            "nom": "Kanda",
            "prenom": "Luc",
            "username": "parentnouveau",
            "password1": "MotDePasseFort12",
            "password2": "MotDePasseFort12",
            "email": "attaquant@evil.test",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("utilisateur:verifier_compte"))
        mock_otp.assert_called_once()
        dest = mock_otp.call_args[0][0]
        self.assertIn("243822222222", dest.replace("+", ""))
        self.assertFalse(Utilisateur.objects.filter(username="parentnouveau").exists())

    @override_settings(INSCRIPTION_WHATSAPP_ACTIF=False)
    @patch("utilisateur.auth_views.envoyer_code_whatsapp")
    def test_inscription_sans_whatsapp_cree_le_compte(self, mock_otp):
        response = self.client.post(reverse("utilisateur:inscription"), {
            "profil": "PARENT",
            "matricule": self.autre_tuteur.matricule,
            "nom": "Kanda",
            "prenom": "Luc",
            "username": "parentdirect",
            "password1": "MotDePasseFort12",
            "password2": "MotDePasseFort12",
            "email": "parentdirect@test.cd",
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse("utilisateur:verifier_compte"))
        mock_otp.assert_not_called()
        self.assertTrue(Utilisateur.objects.filter(username="parentdirect").exists())

    def test_en_tetes_securite(self):
        response = self.client.get(reverse("utilisateur:login"))
        self.assertIn("Content-Security-Policy", response)
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertEqual(response.get("X-Frame-Options"), "DENY")

    def test_media_authentifie(self):
        response = self.client.get("/media/avatars/x.png")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/connexion", response.url)

    def test_media_idor_parent(self):
        from ds.media_views import peut_lire_media

        self.eleve.photo = "photos/eleve-amina.jpg"
        self.eleve.save(update_fields=["photo"])
        self.autre_eleve.photo = "photos/eleve-lea.jpg"
        self.autre_eleve.save(update_fields=["photo"])
        self.assertTrue(peut_lire_media(self.parent, "photos/eleve-amina.jpg"))
        self.assertFalse(peut_lire_media(self.parent, "photos/eleve-lea.jpg"))

    def test_api_moi_parent(self):
        self.client.force_login(self.parent)
        response = self.client.get("/api/moi/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["role"], "PARENT")
        self.assertEqual(len(data["enfants"]), 1)
        self.assertEqual(data["enfants"][0]["id"], self.eleve.pk)

    @override_settings(MFA_WHATSAPP_ACTIF=True)
    @patch("utilisateur.auth_views.envoyer_code_whatsapp", return_value=(True, ""))
    def test_connexion_parent_demande_code_whatsapp(self, mock_otp):
        response = self.client.post(reverse("utilisateur:login"), {
            "username": "parent1",
            "password": "MotDePasseFort12",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("utilisateur:mfa"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        mock_otp.assert_called_once()

    @override_settings(MFA_WHATSAPP_ACTIF=True)
    @patch("utilisateur.auth_views.envoyer_code_whatsapp", return_value=(False, "402"))
    def test_connexion_mfa_echec_envoi_ne_connecte_pas(self, mock_otp):
        response = self.client.post(reverse("utilisateur:login"), {
            "username": "parent1",
            "password": "MotDePasseFort12",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("utilisateur:mfa"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(MFA_WHATSAPP_ACTIF=False)
    def test_connexion_parent_sans_mfa_si_desactive(self):
        response = self.client.post(reverse("utilisateur:login"), {
            "username": "parent1",
            "password": "MotDePasseFort12",
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse("utilisateur:mfa"))
        sessions = SessionConnexion.objects.filter(utilisateur__username="parent1")
        self.assertEqual(sessions.count(), 1)

    def test_connexion_eleve_sans_mfa(self):
        Utilisateur.objects.create_user(
            username="eleve_mfa",
            password="MotDePasseFort12",
            prenom="Amina",
            role="ELEVE",
            ecole=self.ecole,
            eleve=self.eleve,
        )
        response = self.client.post(reverse("utilisateur:login"), {
            "username": "eleve_mfa",
            "password": "MotDePasseFort12",
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse("utilisateur:mfa"))
        sessions = SessionConnexion.objects.filter(utilisateur__username="eleve_mfa")
        self.assertEqual(sessions.count(), 1)
        sess = sessions.get()
        self.assertFalse(sess.revoquee)
        self.assertIsNone(sess.ended_at)
        self.assertTrue(sess.cle_session)

    def test_deconnexion_cloture_la_session(self):
        Utilisateur.objects.create_user(
            username="eleve_sess",
            password="MotDePasseFort12",
            prenom="Amina",
            role="ELEVE",
            ecole=self.ecole,
            eleve=self.eleve,
        )
        self.client.post(reverse("utilisateur:login"), {
            "username": "eleve_sess",
            "password": "MotDePasseFort12",
        })
        sess = SessionConnexion.objects.get(utilisateur__username="eleve_sess")
        self.client.get(reverse("utilisateur:logout"))
        sess.refresh_from_db()
        self.assertIsNotNone(sess.ended_at)
        self.assertFalse(sess.revoquee)

    def test_session_fermee_apres_deux_heures_inactivite(self):
        Utilisateur.objects.create_user(
            username="eleve_idle",
            password="MotDePasseFort12",
            prenom="Amina",
            role="ELEVE",
            ecole=self.ecole,
            eleve=self.eleve,
        )
        self.client.post(reverse("utilisateur:login"), {
            "username": "eleve_idle",
            "password": "MotDePasseFort12",
        })
        sess = SessionConnexion.objects.get(utilisateur__username="eleve_idle")
        SessionConnexion.objects.filter(pk=sess.pk).update(
            last_seen=timezone.now() - timedelta(hours=2, minutes=1),
        )
        response = self.client.get(reverse("utilisateur:portail"), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("utilisateur:login"))
        sess.refresh_from_db()
        self.assertIsNotNone(sess.ended_at)
        self.assertFalse(sess.revoquee)

    def test_session_reste_ouverte_avant_deux_heures(self):
        Utilisateur.objects.create_user(
            username="eleve_actif",
            password="MotDePasseFort12",
            prenom="Amina",
            role="ELEVE",
            ecole=self.ecole,
            eleve=self.eleve,
        )
        self.client.post(reverse("utilisateur:login"), {
            "username": "eleve_actif",
            "password": "MotDePasseFort12",
        })
        sess = SessionConnexion.objects.get(utilisateur__username="eleve_actif")
        SessionConnexion.objects.filter(pk=sess.pk).update(
            last_seen=timezone.now() - timedelta(hours=1),
        )
        response = self.client.get(reverse("utilisateur:portail"), follow=False)
        self.assertEqual(response.status_code, 200)
        sess.refresh_from_db()
        self.assertIsNone(sess.ended_at)

    @patch("utilisateur.auth_views.envoyer_code_whatsapp", return_value=(True, ""))
    @patch("utilisateur.auth_views.generer_code", return_value="123456")
    def test_mot_de_passe_oublie_envoie_code_whatsapp(self, _code, mock_send):
        response = self.client.post(reverse("utilisateur:password_reset"), {
            "identifiant": "parent1",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("utilisateur:password_reset_done"))
        mock_send.assert_called_once()
        suivi = self.client.get(response.url)
        self.assertEqual(suivi.status_code, 200)
        self.assertContains(suivi, "Code de réinitialisation")
        self.assertContains(suivi, "WhatsApp")

    @patch("utilisateur.auth_views.envoyer_code_whatsapp")
    def test_mot_de_passe_oublie_identifiant_inconnu_ne_revele_rien(self, mock_send):
        response = self.client.post(reverse("utilisateur:password_reset"), {
            "identifiant": "inconnu99",
        })
        self.assertEqual(response.status_code, 302)
        mock_send.assert_not_called()
        suivi = self.client.get(response.url)
        self.assertContains(suivi, "Vérifiez WhatsApp")

    @patch("utilisateur.auth_views.envoyer_code_whatsapp", return_value=(True, ""))
    @patch("utilisateur.auth_views.generer_code", return_value="123456")
    def test_mot_de_passe_oublie_cycle_complet(self, _code, _send):
        self.client.post(reverse("utilisateur:password_reset"), {"identifiant": "parent1"})
        response = self.client.post(
            reverse("utilisateur:password_reset_done"),
            {"code": "123456"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("utilisateur:password_reset_confirm"))
        response = self.client.post(reverse("utilisateur:password_reset_confirm"), {
            "new_password1": "NouveauMot12",
            "new_password2": "NouveauMot12",
        })
        self.assertEqual(response.status_code, 302)
        self.parent.refresh_from_db()
        self.assertTrue(self.parent.check_password("NouveauMot12"))
