from datetime import timedelta

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from finances.whatsapp import valider_api_url_whatsapp
from utilisateur.security import otp_peut_renvoyer, payload_otp


class WhatsAppApiUrlTests(SimpleTestCase):
    def test_refuse_http_et_host_interne(self):
        ok, _ = valider_api_url_whatsapp("http://graph.facebook.com/v19.0/x")
        self.assertFalse(ok)
        ok, _ = valider_api_url_whatsapp("https://169.254.169.254/latest")
        self.assertFalse(ok)

    def test_autorise_meta_et_ultramsg(self):
        ok, _ = valider_api_url_whatsapp("https://graph.facebook.com/v19.0/123")
        self.assertTrue(ok)
        ok, _ = valider_api_url_whatsapp("https://api.ultramsg.com/instance1")
        self.assertTrue(ok)


class OtpRenvoiTests(SimpleTestCase):
    @override_settings(OTP_RENVOI_COOLDOWN_SECONDS=60, OTP_RENVOI_MAX=5)
    def test_cooldown_bloque_renvoi_immediat(self):
        payload = payload_otp("123456")
        ok, msg = otp_peut_renvoyer(payload)
        self.assertFalse(ok)
        self.assertIn("Patientez", msg)

    @override_settings(OTP_RENVOI_COOLDOWN_SECONDS=60, OTP_RENVOI_MAX=2)
    def test_plafond_renvois(self):
        payload = payload_otp("123456", extra={"resend_count": 2})
        payload["sent_at"] = (timezone.now() - timedelta(minutes=5)).isoformat()
        ok, msg = otp_peut_renvoyer(payload)
        self.assertFalse(ok)
        self.assertIn("maximal", msg)
