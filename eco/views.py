from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm
from .services import api_get, api_post


# Vista principal: Lista de libros
def index(request):
    """
    Obtiene la lista de libros desde la API y la renderiza.
    """
    # 1. Llamamos al endpoint '/local/' de la API usando nuestro servicio
    # Pasamos 'request' para que, si hay token en sesión, se envíe en el header.
    books = api_get('local/', request)
    
    # Manejo de errores si la API está caída o devuelve error
    if books is None:
        messages.error(request, "No se pudo conectar con el catálogo de libros.")
        books = []

    context = {
        'books': books,
        # Pasamos datos del usuario para mostrar "Hola, Usuario" en el navbar
        'user': request.session.get('user_data') 
    }
    return render(request, 'index.html', context)

# Autenticación: Login
def login_view(request):
    """
    Maneja el login de usuarios.
    1. Envía credenciales a la API (/login/).
    2. Si es exitoso, guarda el Token en la sesión.
    3. Redirige al usuario al índice.
    4. Si falla, muestra mensaje de error.
    """
    # Si el usuario ya está logueado, lo mandamos al inicio
    if request.session.get('auth_token'):
        return redirect('index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # 1. Enviamos credenciales a la API (endpoint /login/)
            # Nota: form.cleaned_data es un diccionario {'username': '...', 'password': '...'}
            response = api_post('login/', form.cleaned_data)
            
            if response and response.status_code == 200:
                data = response.json()
                token = data.get('token')
                
                # 2. Guardamos el Token en la sesión del navegador (Django Session)
                # Esto es CRÍTICO: services.py buscará este valor para futuras peticiones
                request.session['auth_token'] = token
                
                # Guardamos datos básicos para mostrar en el Frontend sin llamar a la API
                request.session['user_data'] = {
                    'username': form.cleaned_data['username']
                }
                
                messages.success(request, "¡Sesión iniciada correctamente!")
                return redirect('index')
            else:
                messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def register_view(request):
    """
    Maneja el registro de nuevos usuarios.
    1. Envía datos a la API (/register/).
    2. Si es exitoso, redirige al login.
    3. Si falla, muestra mensaje de error.
    """
    # Si el usuario ya está logueado, lo mandamos al inicio
    if request.session.get('auth_token'):
        return redirect('index')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # 1. Enviamos datos a la API (endpoint /register/)
            response = api_post('register/', form.cleaned_data)
            
            # 201 Created es el código estándar para creación exitosa
            if response and response.status_code == 201:
                messages.success(request, "Cuenta creada con éxito. Por favor inicia sesión.")
                return redirect('login')
            
            # Intentamos mostrar el error específico que manda la API (ej: "Usuario ya existe")
            error_msg = "Error al registrar usuario."
            if response:
                try:
                    error_msg = str(response.json())
                except Exception:
                    pass
            messages.error(request, error_msg)
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})

# Logout
def logout_view(request):
    """
    Maneja el cierre de sesión de usuarios.
    1. Borra el Token y datos de usuario de la sesión.
    2. Redirige al índice con mensaje de confirmación.
    """
    # Borramos toda la información de la sesión (Token y datos de usuario)
    request.session.flush()
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('index')

# Detalle de libro
def book_detail(request, book_id):
    """
    Muestra toda la info de un libro y permite marcarlo como favorito.
    """
    # 1. Obtener detalle del libro (GET /api/books/local/{id}/)
    book = api_get(f'local/{book_id}/', request)
    
    if not book:
        messages.error(request, "Libro no encontrado.")
        return redirect('index')

    # 2. Verificar si es favorito (Solo si está logueado)
    is_favorite = False
    if request.session.get('auth_token'):
        # Truco: Pedimos la lista de favoritos y vemos si este ID está ahí
        my_favs = api_get('local/my_favorites/', request)
        if my_favs:
            # Verificamos si el ID del libro actual está en la lista de favoritos
            is_favorite = any(f['id'] == int(book_id) for f in my_favs)

    context = {
        'book': book,
        'is_favorite': is_favorite,
        'user': request.session.get('user_data')
    }
    return render(request, 'book_detail.html', context)

# Listar favoritos
def favorites_view(request):
    """
    Lista solo los libros marcados como favoritos por el usuario.
    """
    # Validar login
    if not request.session.get('auth_token'):
        messages.warning(request, "Debes iniciar sesión para ver tus favoritos.")
        return redirect('login')

    # Llamamos al endpoint custom que creamos en el Backend
    books = api_get('local/my_favorites/', request)
    
    if books is None:
        messages.error(request, "Error al cargar favoritos.")
        books = []

    context = {
        'books': books,
        'user': request.session.get('user_data')
    }
    return render(request, 'favorites.html', context)

# Marcar/Desmarcar favorito (Toggle)
def toggle_favorite(request, book_id):
    """
    Vista invisible que procesa el clic en 'Me gusta' y redirige.
    """
    if not request.session.get('auth_token'):
        messages.warning(request, "Inicia sesión para guardar favoritos.")
        return redirect('login')

    # Llamamos al endpoint custom POST /local/{id}/toggle_favorite/
    response = api_post(f'local/{book_id}/toggle_favorite/', {}, request)
    
    if response and response.status_code in [200, 201]:
        data = response.json()
        msg = data.get('message', 'Acción realizada')
        messages.success(request, msg)
    else:
        messages.error(request, "No se pudo actualizar favoritos.")

    # Redirigir a la misma página donde estaba (Detalle)
    return redirect('book_detail', book_id=book_id)