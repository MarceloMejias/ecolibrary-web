from unittest.mock import Mock, patch

import requests  # Importante para simular excepciones reales
from django.test import Client, TestCase
from django.urls import reverse


class ServicesTest(TestCase):
    @patch('eco.services.requests.get') # Ajusta 'eco' por el nombre de tu app si es distinto
    def test_api_get_failure(self, mock_get):
        """api_get debe retornar None cuando la API falla."""
        from eco.services import api_get
        
        # CORRECCIÓN: Usar RequestException en lugar de Exception genérica
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        result = api_get('local/')
        self.assertIsNone(result)

    @patch('eco.services.requests.get')
    def test_api_get_success(self, mock_get):
        from eco.services import api_get
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'title': 'Libro 1'}]
        mock_get.return_value = mock_response

        result = api_get('local/')
        self.assertEqual(result, [{'title': 'Libro 1'}])

    @patch('eco.services.requests.post')
    def test_api_post_failure(self, mock_post):
        """api_post debe retornar None cuando la API falla."""
        from eco.services import api_post
        
        # CORRECCIÓN: Usar RequestException
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        
        result = api_post('register/', {})
        self.assertIsNone(result)

    @patch('eco.services.requests.post')
    def test_api_post_success(self, mock_post):
        from eco.services import api_post
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        result = api_post('register/', {})
        self.assertEqual(result.status_code, 201)

class WebViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_view(self):
        with patch('eco.views.api_get') as mock_api:
            mock_api.return_value = []
            response = self.client.get(reverse('index'))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'index.html')

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_login_view_post_invalid_form(self):
        """Login con formulario inválido debe mostrar errores."""
        response = self.client.post(reverse('login'), {
            'username': '',
            'password': ''
        })
        self.assertEqual(response.status_code, 200)
        # CORRECCIÓN: Ajustado al mensaje por defecto de Django en Inglés
        # Si tu Django está en español, usa 'Este campo es obligatorio.'
        self.assertFormError(response.context['form'], 'username', 'This field is required.')

    def test_register_view_post_success(self):
        """Registro exitoso debe redirigir al login."""
        mock_response = Mock()
        mock_response.status_code = 201
        
        with patch('eco.views.api_post') as mock_api:
            mock_api.return_value = mock_response
            
            response = self.client.post(reverse('register'), {
                'username': 'newuser',
                'email': 'newuser@test.com',
                'password': 'newpass123'
            })
            
            # CORRECCIÓN: Verificamos solo el código 302, sin seguir el link
            # (porque seguirlo requeriría mockear api_get también)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('login'))

    def test_register_view_post_failure(self):
        """Registro fallido debe mostrar error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'username': ['Usuario existe']}
        
        with patch('eco.views.api_post') as mock_api:
            mock_api.return_value = mock_response
            
            response = self.client.post(reverse('register'), {
                'username': 'existing',
                'email': 'test@test.com',
                'password': 'pass'
            })
            
            self.assertEqual(response.status_code, 200)
            # CORRECCIÓN: Buscamos el mensaje JSON crudo que devuelve la vista
            messages = list(response.context['messages'])
            self.assertIn('Usuario existe', str(messages[0]))

    def test_toggle_favorite_success(self):
        """Usuario autenticado puede agregar/quitar favoritos."""
        session = self.client.session
        session['auth_token'] = 'test-token'
        session.save()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'Ok'}
        
        with patch('eco.views.api_post') as mock_api:
            mock_api.return_value = mock_response
            
            response = self.client.get(reverse('toggle_favorite', args=[1]))
            
            # CORRECCIÓN: Verificamos redirección manualmente para evitar cargar la página destino
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('book_detail', args=[1]))