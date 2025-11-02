import os
import sys

from django.core.wsgi import get_wsgi_application

path = "/home/TTFlick/E-commerce"
if path not in sys.path:
    sys.path.append(path)

os.environ["DJANGO_SETTINGS_MODULE"] = "root.settings"

application = get_wsgi_application()
