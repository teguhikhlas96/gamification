from django.shortcuts import redirect
from django.urls import reverse


class RoleBasedRedirectMiddleware:
    """
    Middleware untuk redirect user berdasarkan role setelah login
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Path yang tidak perlu di-redirect
        self.exempt_paths = [
            '/admin/',
            '/accounts/login/',
            '/accounts/register/',
            '/accounts/logout/',
            '/static/',
            '/media/',
        ]

    def __call__(self, request):
        # Cek jika path perlu di-exempt
        if any(request.path.startswith(path) for path in self.exempt_paths):
            response = self.get_response(request)
            return response

        # Jika user sudah login dan mengakses root atau path tertentu
        if request.user.is_authenticated:
            # Jika user mengakses root, redirect berdasarkan role
            if request.path == '/':
                if request.user.is_admin():
                    return redirect('admin_dashboard:dashboard')
                elif request.user.is_player():
                    return redirect('player:dashboard')
            
            # Redirect jika user mengakses dashboard yang salah
            if request.path.startswith('/admin-dashboard/') and not request.user.is_admin():
                return redirect('player:dashboard')
            elif request.path.startswith('/player-dashboard/') and not request.user.is_player():
                return redirect('admin_dashboard:dashboard')

        response = self.get_response(request)
        return response

