import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_HOSTS = []

DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
    }
}

INSTALLED_APPS = (
        'db',
)

SECRET_KEY = 'notsecret'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CONN_MAX_AGE = 200

USE_TZ = True
TIME_ZONE = "Etc/GMT+0"
