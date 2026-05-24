from django.utils.deprecation import MiddlewareMixin


class NoCacheMiddleware(MiddlewareMixin):
    """Prevent caching of protected pages to avoid showing them on browser back/undo"""
    
    def process_response(self, request, response):
        # Add cache control headers for all responses
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
