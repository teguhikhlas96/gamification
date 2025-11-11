"""
Custom middleware untuk error handling dan security
"""
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Middleware untuk handle errors dan provide user-friendly feedback"""
    
    def process_exception(self, request, exception):
        """Handle exceptions dan return user-friendly error messages"""
        # Log the exception
        logger.error(f"Exception in {request.path}: {str(exception)}", exc_info=True)
        
        # Handle specific exceptions
        if isinstance(exception, PermissionDenied):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Permission denied'}, status=403)
            from django.contrib import messages
            messages.error(request, 'You do not have permission to perform this action.')
            from django.shortcuts import redirect
            return redirect('accounts:login')
        
        if isinstance(exception, ValidationError):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(exception)}, status=400)
            from django.contrib import messages
            messages.error(request, f'Validation error: {str(exception)}')
            return None
        
        if isinstance(exception, IntegrityError):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Database integrity error. Please try again.'}, status=400)
            from django.contrib import messages
            messages.error(request, 'An error occurred. Please try again.')
            return None
        
        # For other exceptions, return None to let Django handle it
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware untuk add security headers"""
    
    def process_response(self, request, response):
        """Add security headers to response"""
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Type Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Frame Options
        response['X-Frame-Options'] = 'DENY'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (basic)
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self' ws: wss:;"
        )
        
        return response

