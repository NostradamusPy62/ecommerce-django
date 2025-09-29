from django.shortcuts import redirect
from django.conf import settings
from django.contrib import messages

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # URLs que requieren permisos de admin
        admin_urls = ['/admin-panel/', '/admin-panel/dashboard/', '/admin-panel/products/', 
                     '/admin-panel/categories/', '/admin-panel/users/']
        
        # URLs que requieren permisos de staff (vendedor o admin)
        staff_urls = ['/admin-panel/orders/', '/admin-panel/reports/', '/admin-panel/sales/']

        current_path = request.path

        # Verificar acceso a URLs de admin
        if any(current_path.startswith(url) for url in admin_urls):
            if not request.user.is_authenticated:
                messages.error(request, 'Debes iniciar sesión para acceder al panel de administración.')
                return redirect('login')
            
            if not (request.user.is_admin or request.user.is_superadmin):
                messages.error(request, 'No tienes permisos para acceder al panel de administración.')
                return redirect('home')

        # Verificar acceso a URLs de staff
        elif any(current_path.startswith(url) for url in staff_urls):
            if not request.user.is_authenticated:
                messages.error(request, 'Debes iniciar sesión para acceder a esta sección.')
                return redirect('login')
            
            if not (request.user.is_staff or request.user.is_admin or request.user.is_superadmin):
                messages.error(request, 'No tienes permisos para acceder a esta sección.')
                return redirect('home')

class RedirectAfterLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Si el usuario acaba de iniciar sesión y tiene permisos de admin
        if (request.user.is_authenticated and 
            request.path == '/' and  # Cuando llegan al home después del login
            (request.user.is_superadmin or request.user.is_admin or request.user.is_staff) and
            'admin-panel' not in request.META.get('HTTP_REFERER', '')):
            
            # Solo redirigir si vienen del login (evitar loop)
            if 'login' in request.META.get('HTTP_REFERER', ''):
                messages.info(request, f'Bienvenido al Panel de Control, {request.user.first_name}!')
                return redirect('admin_panel:dashboard')
        
        return None