from django.shortcuts import redirect

AUTHORIZED_EMAILS = {
    "valentinagalo12@gmail.com",
    "mauriciocasals90@gmail.com",
}

class AuthRequiredMiddleware:
    """
    Middleware que restringe el acceso a todo el sitio a menos que
    el usuario haya iniciado sesión con las credenciales autorizadas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # Rutas públicas permitidas sin inicio de sesión
        if (
            path.startswith('/login/') or
            path.startswith('/static/') or
            path.startswith('/media/') or
            path.startswith('/admin/')
        ):
            return self.get_response(request)

        # Validación de usuarios autorizados
        user_session = request.session.get('authenticated_user', '').lower()
        is_authenticated = (
            user_session in AUTHORIZED_EMAILS or
            (request.user.is_authenticated and (
                request.user.username.lower() in AUTHORIZED_EMAILS or 
                request.user.email.lower() in AUTHORIZED_EMAILS
            ))
        )

        if not is_authenticated:
            return redirect('/login/')

        return self.get_response(request)
