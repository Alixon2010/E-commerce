from django.utils import translation

class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang_code = "en"

        user = getattr(request, "user", None)
        if user and user.is_authenticated and hasattr(user, "language"):
            lang_code = user.language

        translation.activate(lang_code)
        request.LANGUAGE_CODE = lang_code

        response = self.get_response(request)
        translation.deactivate()
        return response
