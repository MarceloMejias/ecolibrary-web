from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import LoginForm, RegisterForm
from .services import api_get, api_post


# Funciones Auxiliares
def _is_authenticated(request):
    """Verifica si el usuario tiene token de autenticación."""
    return bool(request.session.get('auth_token'))


def _get_user_data(request):
    """Obtiene datos del usuario desde la sesión."""
    return request.session.get('user_data')


def _save_session_data(request, token, username):
    """Guarda token y datos de usuario en la sesión."""
    request.session['auth_token'] = token
    request.session['user_data'] = {'username': username}


def _get_error_message(response, default_message):
    """Extrae mensaje de error de la respuesta API."""
    if not response:
        return default_message
    
    try:
        return str(response.json())
    except Exception:
        return default_message


def _check_book_in_favorites(favorites, book_id):
    """Verifica si un libro está en la lista de favoritos."""
    if not favorites:
        return False
    return any(f.get('id') == int(book_id) for f in favorites)


# Vistas Principales

@require_GET
def index(request):
    """Muestra el catálogo de libros."""
    books = api_get('local/', request) or []
    
    if books == []:
        messages.error(request, "No se pudo conectar con el catálogo de libros.")

    context = {
        'books': books,
        'user': _get_user_data(request)
    }
    return render(request, 'index.html', context)

@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """Maneja el inicio de sesión de usuarios."""
    if _is_authenticated(request):
        return redirect('index')

    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'login.html', {'form': form})

    # POST
    form = LoginForm(request.POST)
    if not form.is_valid():
        return render(request, 'login.html', {'form': form})

    response = api_post('login/', form.cleaned_data)
    
    if not response or response.status_code != 200:
        messages.error(request, "Usuario o contraseña incorrectos.")
        return render(request, 'login.html', {'form': form})

    data = response.json()
    token = data.get('token')
    
    if token:
        _save_session_data(request, token, form.cleaned_data['username'])
        messages.success(request, "¡Sesión iniciada correctamente!")
        return redirect('index')
    
    messages.error(request, "Error al procesar la respuesta.")
    return render(request, 'login.html', {'form': form})


@require_http_methods(["GET", "POST"])
@csrf_protect
def register_view(request):
    """Maneja el registro de nuevos usuarios."""
    if _is_authenticated(request):
        return redirect('index')

    if request.method == 'GET':
        form = RegisterForm()
    else:
        # POST
        form = RegisterForm(request.POST)
        if not form.is_valid():
            return render(request, 'register.html', {'form': form})

        response = api_post('register/', form.cleaned_data)
        
        if response and response.status_code == 201:
            messages.success(request, "Cuenta creada con éxito. Por favor inicia sesión.")
            return redirect('login')
        
        error_msg = _get_error_message(response, "Error al registrar usuario.")
        messages.error(request, error_msg)

    return render(request, 'register.html', {'form': form})


@require_POST
def logout_view(request):
    """Cierra la sesión del usuario."""
    request.session.flush()
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('index')

@require_GET
def book_detail(request, book_id):
    """Muestra el detalle de un libro."""
    book = api_get(f'local/{book_id}/', request)
    
    if not book:
        messages.error(request, "Libro no encontrado.")
        return redirect('index')

    is_favorite = False
    if _is_authenticated(request):
        favorites = api_get('local/my_favorites/', request)
        is_favorite = _check_book_in_favorites(favorites, book_id)

    context = {
        'book': book,
        'is_favorite': is_favorite,
        'user': _get_user_data(request)
    }
    return render(request, 'book_detail.html', context)

@require_GET
def favorites_view(request):
    """Muestra los libros favoritos del usuario."""
    if not _is_authenticated(request):
        messages.warning(request, "Debes iniciar sesión para ver tus favoritos.")
        return redirect('login')

    books = api_get('local/my_favorites/', request) or []
    
    if books == []:
        messages.error(request, "Error al cargar favoritos.")

    context = {
        'books': books,
        'user': _get_user_data(request)
    }
    return render(request, 'favorites.html', context)

@require_POST
@csrf_protect
def toggle_favorite(request, book_id):
    """Agrega o quita un libro de favoritos."""
    if not _is_authenticated(request):
        messages.warning(request, "Inicia sesión para guardar favoritos.")
        return redirect('login')

    response = api_post(f'local/{book_id}/toggle_favorite/', {}, request)
    
    if response and response.status_code in [200, 201]:
        data = response.json()
        msg = data.get('message', 'Acción realizada')
        messages.success(request, msg)
    else:
        messages.error(request, "No se pudo actualizar favoritos.")

    return redirect('book_detail', book_id=book_id)