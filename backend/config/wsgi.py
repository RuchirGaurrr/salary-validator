"""
config/wsgi.py — Web Server Gateway Interface entry point
Render uses this file to start your Django server. You don't need to edit this.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
