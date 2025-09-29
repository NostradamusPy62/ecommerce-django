from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from functools import wraps

def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_superadmin:
            return HttpResponseForbidden("No tienes permisos de superadministrador")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_admin or request.user.is_superadmin):
            return HttpResponseForbidden("No tienes permisos de administrador")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def staff_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.is_admin or request.user.is_superadmin):
            return HttpResponseForbidden("No tienes permisos de staff")
        return view_func(request, *args, **kwargs)
    return _wrapped_view