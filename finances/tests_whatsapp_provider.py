from django.test import TestCase, override_settings

from finances.models import ConfigWhatsApp
from finances.whatsapp import _langues_meta_a_essayer, provider_effectif


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
