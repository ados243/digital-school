from django.test import TestCase, override_settings

from finances.models import ConfigWhatsApp
from finances.whatsapp import provider_effectif


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
