# Create your tests here.
from django.test import Client, TestCase
from django.urls import reverse


class WebViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_view(self):
        """El home debe cargar y usar el template correcto"""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_login_view_get(self):
        """El login debe cargar el formulario"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_register_view_get(self):
        """El registro debe cargar el formulario"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')