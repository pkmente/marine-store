import os
import sys
from pathlib import Path

# Add project root (where manage.py lives) to PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Point Django at the correct settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marine_store.settings")

from django.core.wsgi import get_wsgi_application

# Vercel expects an `app` or `application` callable
app = application = get_wsgi_application()
