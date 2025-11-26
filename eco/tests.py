"""
Tests para la aplicación eco (Frontend Web).

Cubre las vistas principales, formularios, servicios y flujos de autenticación.
"""

from unittest.mock import Mock, patch

from django.test import Client, TestCase
from django.urls import reverse

from .forms import LoginForm, RegisterForm


class WebViewsTest(TestCase):
    """Tests para las vistas del frontend."""

    def setUp(self):
        """Configuración inicial para cada test."""
        self.client = Client()

    def test_index_view_success(self):
        """El home debe cargar y usar el template correcto con libros."""
        with patch('eco.views.api_get') as mock_api:
            mock_api.return_value = [
                {'id': 1, 'title': 'Test Book', 'author': 'Test Author'}
            ]
            
            response = self.client.get(reverse('index'))
            
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'index.html')
            self.assertIn('books', response.context)
            self.assertEqual(len(response.context['books']), 1)

    def test_index_view_api_failure(self):
        """El home debe manejar fallos de la API mostrando lista vacía."""
        with patch('eco.views.api_get') as mock_api:
            mock_api.return_value = None
            
            response = self.client.get(reverse('index'))
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['books'], [])
            messages = list(response.context['messages'])
            self.assertEqual(len(messages), 1)
            self.assertIn('No se pudo conectar', str(messages[0]))

    def test_login_view_get(self):
        """El login debe cargar el formulario."""
        response = self.client.get(reverse('login'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertIsInstance(response.context['form'], LoginForm)

    def test_login_view_already_authenticated(self):
        """Usuario ya autenticado debe ser redirigido al index."""
        session = self.client.session
        session['auth_token'] = 'test-token-123'
        session.save()
        
        response = self.client.get(reverse('login'))
        
        self.assertRedirects(response, reverse('index'))

    def test_login_view_post_success(self):
        """Login exitoso debe guardar token en sesión y redirigir."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'token': 'valid-token-456'}
        
        with patch('eco.views.api_post') as mock_api:
            mock_api.return_value = mock_response
            
            response = self.client.post(reverse('login'), {
                'username': 'testuser',
                'password': 'testpass123'
            })
            
            self.assertRedirects(response, reverse('index'))
            self.assertEqual(self.client.session['auth_token'], 'valid-token-456')
            self.assertEqual(
                self.client.session['user_data']['username'], 
                'testuser'
            )

    def test_login_view_post_invalid_credentials(self):
        """Login con credenciales incorrectas debe mostrar error."""
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch('eco.views.api_post') as mock_api:
            mock_api.return_value = mock_response
            
            response = self.client.post(reverse('login'), {
                'username': 'wronguser',
                'password': 'wrongpass'
            })
            
            self.assertEqual(response.status_code, 200)
            messages = list(response.context['messages'])
            self.assertIn('Usuario o contraseña incorrectos', str(messages[0]))

    def test_login_view_post_invalid_form(self):
        """Login con formulario inválido debe mostrar errores."""
        response = self.client.post(reverse('login'), {
            'username': '',
            'password': ''
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'username', 'Este campo es obligatorio.')

    def test_register_view_get(self):
        """El registro debe cargar el formulario."""
        response = self.client.get(reverse('register'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
        self.assertIsInstance(response.context['form'], RegisterForm)

    def test_register_view_already_authenticated(self):
        """Usuario ya autenticado debe ser redirigido al index."""
        session = self.client.session
        session['auth_token'] = 'test-token-123'
        session.save()
        
        response = self.client.get(reverse('register'))
        
        self.assertRedirects(response, reverse('index'))

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
            
            self.assertRedirects(response, reverse('login'))
            messages = list(response.context['messages'])
            self.assertIn('Cuenta creada con éxito', str(messages[0]))

    def test_register_view_post_failure(self):
        """Registro fallido debe mostrar error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'username': ['Este nombre de usuario ya existe.']}
        
        with patch('eco.views.api_post') as mock_api:
            mock_api.return_value = mock_response
            
            response = self.client.post(reverse('register'), {
                'username': 'existinguser',
                'email': 'test@test.com',
                'password': 'pass123'
            })
            
            self.assertEqual(response.status_code, 200)
            messages = list(response.context['messages'])
            self.assertIn('Error al registrar', str(messages[0]))

    def test_logout_view(self):
        """Logout debe limpiar la sesión y redirigir al index."""
        session = self.client.session
        session['auth_token'] = 'test-token-123'
        session['user_data'] = {'username': 'testuser'}
        session.save()
        
        response = self.client.get(reverse('logout'))
        
        self.assertRedirects(response, reverse('index'))
        self.assertNotIn('auth_token', self.client.session)
        self.assertNotIn('user_data', self.client.session)

    def test_book_detail_success(self):
        """Detalle de libro debe mostrar información correcta."""
        mock_book = {
            'id': 1,
            'title': 'Test Book',
            'author': 'Author Name',
            'description': 'Description'
        }
        
        with patch('eco.views.api_get') as mock_api:
            mock_api.return_value = mock_book
            
            response = self.client.get(reverse('book_detail', args=[1]))
            
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'book_detail.html')
            self.assertEqual(response.context['book']['title'], 'Test Book')
            self.assertFalse(response.context['is_favorite'])

    def test_book_detail_authenticated_with_favorite(self):
        """Usuario autenticado ve si el libro está en favoritos."""
        session = self.client.session
        session['auth_token'] = 'test-token-123'
        session.save()
        
        mock_book = {'id': 1, 'title': 'Test Book'}
        mock_favorites = [{'id': 1}, {'id': 2}]
        
        with patch('eco.views.api_get') as mock_api:
            mock_api.side_effect = [mock_book, mock_favorites]
            
            response = self.client.get(reverse('book_detail', args=[1]))
            
            self.assertTrue(response.context['is_favorite'])

    def test_book_detail_not_found(self):
        """Libro no encontrado debe redirigir al index."""
        with patch('eco.views.api_get') as mock_api:
            mock_api.return_value = None
            
            response = self.client.get(reverse('book_detail', args=[999]))
            
            self.assertRedirects(response, reverse('index'))

    def test_favorites_view_not_authenticated(self):
        """Usuario no autenticado debe ser redirigido al login."""
        response = self.client.get(reverse('favorites'))
        
        self.assertRedirects(response, reverse('login'))

    def test_favorites_view_success(self):
        """Usuario autenticado ve su lista de favoritos."""
        session = self.client.session
        session['auth_token'] = 'test-token-123'
        session.save()
        
        mock_favorites = [
            {'id': 1, 'title': 'Favorite 1'},
            {'id': 2, 'title': 'Favorite 2'}
        ]
        
        with patch('eco.views.api_get') as mock_api:
            mock_api.return_value = mock_favorites
            
            response = self.client.get(reverse('favorites'))
            
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'favorites.html')
            self.assertEqual(len(response.context['books']), 2)

    def test_toggle_favorite_not_authenticated(self):
        """Usuario no autenticado no puede agregar favoritos."""
        response = self.client.get(reverse('toggle_favorite', args=[1]))
        
        self.assertRedirects(response, reverse('login'))

    def test_toggle_favorite_success(self):
        """Usuario autenticado puede agregar/quitar favoritos."""
        session = self.client.session
        session['auth_token'] = 'test-token-123'
        session.save()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'Agregado a favoritos'}
        
        with patch('eco.views.api_post') as mock_api:
            mock_api.return_value = mock_response
            
            response = self.client.get(reverse('toggle_favorite', args=[1]))
            
            self.assertRedirects(response, reverse('book_detail', args=[1]))


class FormsTest(TestCase):
    """Tests para los formularios."""

    def test_login_form_valid(self):
        """LoginForm debe ser válido con datos correctos."""
        form = LoginForm(data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertTrue(form.is_valid())

    def test_login_form_invalid_empty(self):
        """LoginForm debe ser inválido sin datos."""
        form = LoginForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 2)

    def test_register_form_valid(self):
        """RegisterForm debe ser válido con datos correctos."""
        form = RegisterForm(data={
            'username': 'newuser',
            'email': 'test@example.com',
            'password': 'securepass123'
        })
        self.assertTrue(form.is_valid())

    def test_register_form_invalid_email(self):
        """RegisterForm debe ser inválido con email incorrecto."""
        form = RegisterForm(data={
            'username': 'newuser',
            'email': 'invalid-email',
            'password': 'pass123'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class ServicesTest(TestCase):
    """Tests para los servicios de API."""

    @patch('eco.services.requests.get')
    def test_api_get_success(self, mock_get):
        """api_get debe retornar datos cuando la API responde correctamente."""
        from eco.services import api_get
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response
        
        result = api_get('local/')
        
        self.assertEqual(result, {'data': 'test'})
        mock_get.assert_called_once()

    @patch('eco.services.requests.get')
    def test_api_get_failure(self, mock_get):
        """api_get debe retornar None cuando la API falla."""
        from eco.services import api_get
        
        mock_get.side_effect = Exception('Connection error')
        
        result = api_get('local/')
        
        self.assertIsNone(result)

    @patch('eco.services.requests.post')
    def test_api_post_success(self, mock_post):
        """api_post debe retornar response cuando la API responde."""
        from eco.services import api_post
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = api_post('register/', {'username': 'test'})
        
        self.assertEqual(result.status_code, 201)
        mock_post.assert_called_once()

    @patch('eco.services.requests.post')
    def test_api_post_failure(self, mock_post):
        """api_post debe retornar None cuando la API falla."""
        from eco.services import api_post
        
        mock_post.side_effect = Exception('Connection error')
        
        result = api_post('register/', {})
        
        self.assertIsNone(result)