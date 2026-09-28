from django.test import RequestFactory, SimpleTestCase, override_settings

from core.error_views import handler404, handler500


@override_settings(DEBUG=False)
class ErrorPageTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/missing/")
        self.request.session = {}

    def test_404_is_branded_russian_page_with_home_link(self):
        response = handler404(self.request, RuntimeError("private exception text"))
        body = response.content.decode()

        self.assertEqual(response.status_code, 404)
        self.assertIn("Страница не найдена", body)
        self.assertIn("ApexGrid", body)
        self.assertIn('href="/"', body)
        self.assertNotIn("private exception text", body)

    def test_500_is_branded_russian_page_without_exception_details(self):
        response = handler500(self.request)
        body = response.content.decode()

        self.assertEqual(response.status_code, 500)
        self.assertIn("Технический пит-стоп", body)
        self.assertIn("ApexGrid", body)
        self.assertIn('href="/"', body)
        self.assertNotIn("Traceback", body)
