from django.core.management.base import BaseCommand, CommandError

from ds.bird import BirdError, bird_configure, envoyer_email_bird, envoyer_whatsapp_bird


class Command(BaseCommand):
    help = "Envoie un e-mail (et optionnellement un WhatsApp) de test via Bird."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            default="delivered@messagebird.dev",
            help="Destinataire e-mail (défaut : sandbox Bird).",
        )
        parser.add_argument("--whatsapp", default="", help="Numéro E.164, ex. +2438…")
        parser.add_argument(
            "--template",
            default="",
            help="Slug du template WhatsApp (sinon BIRD_WHATSAPP_TEMPLATE).",
        )

    def handle(self, *args, **options):
        if not bird_configure():
            raise CommandError("BIRD_API_KEY est vide. Ajoutez-la dans le fichier .env.")

        destinataire = options["to"]
        self.stdout.write(f"Envoi e-mail Bird vers {destinataire}…")
        try:
            msg_id, status = envoyer_email_bird(
                [destinataire],
                "Test Digital School — Bird",
                "Ceci est un e-mail de test d'authentification Digital School via Bird.",
                html="<p>Ceci est un e-mail de test <strong>Digital School</strong> via Bird.</p>",
            )
            self.stdout.write(self.style.SUCCESS(f"E-mail accepté : {msg_id} ({status})"))
        except BirdError as exc:
            self.stdout.write(self.style.WARNING(f"E-mail : {exc}"))
            if "emails:write" in str(exc):
                self.stdout.write(
                    "La cle n'a pas le droit d'envoyer des e-mails. "
                    "Dans Bird > API keys, ajoutez le scope emails:write."
                )

        numero = (options["whatsapp"] or "").strip()
        if not numero:
            return
        from django.conf import settings
        template = (options["template"] or settings.BIRD_WHATSAPP_TEMPLATE or "bird_otp").strip()
        if template == "bird_delivery_update":
            components = [{
                "type": "body",
                "parameters": [
                    {"type": "text", "name": "ref", "text": "DS-TEST"},
                    {"type": "text", "name": "date", "text": "18 Aug 2026"},
                ],
            }]
            language = "en"
        else:
            components = [{
                "type": "body",
                "parameters": [{"type": "text", "text": "123456"}],
            }]
            language = settings.BIRD_WHATSAPP_LANGUAGE
        self.stdout.write(f"Envoi WhatsApp Bird vers {numero} (template {template})…")
        try:
            wa_id, wa_status = envoyer_whatsapp_bird(
                numero,
                template,
                components=components,
                language=language,
            )
        except BirdError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"WhatsApp accepté : {wa_id} ({wa_status})"))
