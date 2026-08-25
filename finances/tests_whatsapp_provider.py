from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from finances.models import ConfigWhatsApp
from finances.whatsapp import (
    _langues_meta_a_essayer,
    message_echec_otp,
    provider_effectif,
)


class WhatsAppProviderEffectifTests(TestCase):
    def setUp(self):
        self.config = ConfigWhatsApp.charger_centrale()

    @override_settings(BIRD_API_KEY="bk_eu1_test")
    def test_meta_choisi_malgre_bird_key(self):
        self.config.provider = "META"
        self.assertEqual(provider_effectif(self.config), "META")

    @override_settings(BIRD_API_KEY="bk_eu1_test")
    def test_bird_explicite_avec_cle(self):
        self.config.provider = "BIRD"
        self.assertEqual(provider_effectif(self.config), "BIRD")

    @override_settings(BIRD_API_KEY="")
    def test_ultramsg_sans_bird(self):
        self.config.provider = "ULTRAMSG"
        self.assertEqual(provider_effectif(self.config), "ULTRAMSG")


class WhatsAppLangueMetaTests(TestCase):
    def test_fr_puis_fr_FR(self):
        self.assertEqual(_langues_meta_a_essayer("fr"), ["fr", "fr_FR"])

    def test_fr_FR_puis_fr(self):
        self.assertEqual(_langues_meta_a_essayer("fr_FR"), ["fr_FR", "fr"])

    def test_otp_payload_inclut_bouton(self):
        from finances.whatsapp import _construire_payload_meta_template

        payload = _construire_payload_meta_template(
            "243812903591",
            "code_verification",
            "fr",
            ["123456"],
            extra_components=[
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": "123456"}],
                }
            ],
        )
        composants = payload["template"]["components"]
        self.assertEqual(composants[0]["type"], "body")
        self.assertEqual(composants[1]["type"], "button")
        self.assertEqual(composants[1]["parameters"][0]["text"], "123456")

    def test_otp_langues_incluent_anglais(self):
        self.assertEqual(
            _langues_meta_a_essayer("fr", extras=["en", "en_US"]),
            ["fr", "fr_FR", "en", "en_US"],
        )

    def test_message_echec_otp_132001(self):
        msg = message_echec_otp(
            'HTTP 404: {"error":{"code":132001,"message":"Template name does not exist in the translation"}}',
            "code_verification",
        )
        self.assertIn("code_verification", msg)
        self.assertIn("Authentification", msg)

    @patch("finances.whatsapp._token_clair", return_value="tok")
    @patch("finances.whatsapp.requests.post")
    def test_otp_envoie_copy_code_en_premier(self, mock_post, _token):
        from finances.whatsapp import envoyer_otp_meta

        mock_post.return_value = MagicMock(
            ok=True, status_code=200, text='{"messages":[{"id":"wamid.1"}]}'
        )
        config = ConfigWhatsApp.charger_centrale()
        config.instance_id = "1194724093733471"
        config.template_otp = "code_verification"
        config.template_langue = "fr"
        ok, _, err = envoyer_otp_meta(config, "243812903591", "654321")
        self.assertTrue(ok)
        self.assertEqual(err, "")
        payload = mock_post.call_args.kwargs["json"]
        bouton = payload["template"]["components"][1]
        self.assertEqual(bouton["sub_type"], "copy_code")
        self.assertEqual(bouton["parameters"][0]["type"], "coupon_code")
        self.assertEqual(bouton["parameters"][0]["coupon_code"], "654321")

    @patch("finances.whatsapp._token_clair", return_value="tok")
    @patch("finances.whatsapp.requests.post")
    def test_otp_ne_persiste_pas_la_langue_fr_FR(self, mock_post, _token):
        from finances.whatsapp import envoyer_otp_meta

        def side_effect(*args, **kwargs):
            lang = kwargs["json"]["template"]["language"]["code"]
            resp = MagicMock()
            if lang == "fr_FR":
                resp.ok = True
                resp.status_code = 200
                resp.text = '{"messages":[{"id":"1"}]}'
            else:
                resp.ok = False
                resp.status_code = 404
                resp.text = (
                    '{"error":{"code":132001,'
                    '"message":"(#132001) Template name does not exist in the translation"}}'
                )
            return resp

        mock_post.side_effect = side_effect
        config = ConfigWhatsApp.charger_centrale()
        config.instance_id = "1"
        config.template_langue = "fr"
        config.save(update_fields=["instance_id", "template_langue"])
        ok, _, _ = envoyer_otp_meta(config, "243000000", "111111")
        self.assertTrue(ok)
        config.refresh_from_db()
        self.assertEqual(config.template_langue, "fr")

    def test_langue_en_devient_fr(self):
        from finances.whatsapp import langue_template

        config = ConfigWhatsApp.charger_centrale()
        config.template_langue = "en"
        self.assertEqual(langue_template(config), "fr")
