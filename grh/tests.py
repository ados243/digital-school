from django.test import SimpleTestCase


class GrhSmokeTests(SimpleTestCase):
    def test_module_importable(self):
        import grh.views  # noqa: F401
