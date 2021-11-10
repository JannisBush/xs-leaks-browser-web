"""
WSGI config for leakyservice project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakyservice.settings')

application = get_wsgi_application()

# Code executed when the server starts, imports have to be below get_wsgi_application()
from django.contrib.auth.models import User
import logging
logger = logging.getLogger(__name__)
# Create test user if not exist already
u, created = User.objects.get_or_create(username="test")
if created:
    logger.info("User was created")
    u.set_password("team40web")
    u.save()
else:
    logger.info("User did exist already")
