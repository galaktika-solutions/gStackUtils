# import os
# import re
import logging.config

from django.utils.translation import ugettext_lazy as _
from gstackutils.conf import Config


# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config = Config()

SECRET_KEY = config.get("DJANGO_SECRET_KEY")

DEBUG = config.get("DJANGO_DEBUG")

ALLOWED_HOSTS = config.get("HOST_NAMES")

ADMINS = config.get("ADMINS")

# # Email related settings
# EMAIL_HOST = os.environ.get('EMAIL_HOST')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 0)) or None
# EMAIL_HOST_USER = read_secret_from_file('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = read_secret_from_file('EMAIL_HOST_PASSWORD')
# EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '').lower() == 'true'
# EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', '').lower() == 'true'
# EMAIL_TIMEOUT = 10

SERVER_EMAIL = config.get("SERVER_EMAIL")
# DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')
EMAIL_SUBJECT_PREFIX = '[%s] ' % ALLOWED_HOSTS[0]

# EMAIL_BACKEND = 'mailer.backend.DbBackend'
EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
SENDGRID_API_KEY = config.get("SENDGRID_API_KEY")
# SENDGRID_SANDBOX_MODE_IN_DEBUG = False

# MAILER_EMAIL_BACKEND = 'core.rewrite_email_backend.EmailBackend'
# MAILER_LOCK_PATH = '/tmp/mailer_lock'


STATIC_URL = '/static/'
STATIC_ROOT = '/src/static/'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MEDIA_ROOT = '/data/files/'
MEDIA_URL = '/media/'

ROOT_URLCONF = 'core.urls'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "demo.apps.DemoConfig",
    "user.apps.UserConfig",
    # 'django_extensions',
    # 'mailer',
    # 'channels',
    # 'rest_framework.apps.RestFrameworkConfig',
    # 'django_filters',
    # 'rest_framework.authtoken',
    # 'rest_auth',
    # 'explorer.apps.ExplorerAppConfig',
    # 'core.apps.Config',
    # 'rosetta.apps.RosettaAppConfig',
    # 'improveduser.apps.Config',
    # 'demo.apps.Config',
]

# # explorer has an issue, when it is fixed, we can remove this.
# MIGRATION_MODULES = {
#     'explorer': 'core.explorer_migrations',
# }
#
# # debug toolbar installs a log handler (ThreadTrackingHandler) on the root
# # logger which conflicts with mailer's management command
# if DEBUG and not os.environ.get('NO_DEBUG_TOOLBAR', ''):
#     INSTALLED_APPS.append('debug_toolbar')
#     MIDDLEWARE.append(
#         'debug_toolbar.middleware.DebugToolbarMiddleware'
#     )
#     DEBUG_TOOLBAR_CONFIG = {
#         'SHOW_TOOLBAR_CALLBACK': lambda x: DEBUG
#     }

AUTH_PREFIX = 'django.contrib.auth.password_validation'
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': f"{AUTH_PREFIX}.UserAttributeSimilarityValidator",
        'OPTIONS': {
            'user_attributes': ('email', 'full_name', 'short_name')
        },
    },
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
# # ASGI_APPLICATION = "core.routing.application"
#
# # CHANNEL_LAYERS = {
# #     'default': {
# #         'BACKEND': 'channels_redis.core.RedisChannelLayer',
# #         'CONFIG': {
# #             "hosts": [('redis', 6379)],
# #         },
# #     },
# # }

# Set up custom user model
AUTH_USER_MODEL = 'user.User'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'postgres',
        'PORT': '5432',
        'NAME': 'django',
        'USER': 'django',
        'PASSWORD': config.get('DB_PASSWORD_DJANGO'),
        # 'OPTIONS': {
        #     'sslmode': 'verify-ca',
        #     'sslrootcert': '/run/secrets/PG_SERVER_SSL_CACERT',
        #     'sslcert': '/run/secrets/PG_CLIENT_SSL_CERT',
        #     'sslkey': '/run/secrets/PG_CLIENT_SSL_KEY',
        # },
    },
    # 'explorer': {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'HOST': 'postgres',
    #     'PORT': '5432',
    #     'NAME': 'django',
    #     'USER': 'explorer',
    #     'PASSWORD': read_secret_from_file('DB_PASSWORD_EXPLORER'),
    #     'TEST': {
    #         'MIRROR': 'default',
    #     },
    #     'OPTIONS': {
    #         'sslmode': 'verify-ca',
    #         'sslrootcert': '/run/secrets/PG_SERVER_SSL_CACERT',
    #         'sslcert': '/run/secrets/PG_CLIENT_SSL_CERT',
    #         'sslkey': '/run/secrets/PG_CLIENT_SSL_KEY',
    #     },
    # },
}

# REST_FRAMEWORK = {
#     'DEFAULT_PERMISSION_CLASSES': (
#         'rest_framework.permissions.IsAuthenticated',
#     ),
#     # Use this if you want to disable the form on the BrowsableAPIRenderer
#     # 'DEFAULT_RENDERER_CLASSES': (
#     #     'rest_framework.renderers.JSONRenderer',
#     #     'core.renderers.BrowsableAPIRendererWithoutForm',
#     # ),
#     'DEFAULT_FILTER_BACKENDS': (
#         'django_filters.rest_framework.DjangoFilterBackend',
#     ),
#     'DEFAULT_PAGINATION_CLASS': (
#         'core.pagination.FlexiblePagination'
#     ),
# }
#
# EXPLORER_DEFAULT_CONNECTION = 'explorer'
# EXPLORER_CONNECTIONS = {'Default': 'explorer'}
# EXPLORER_SQL_BLACKLIST = ()
# EXPLORER_DATA_EXPORTERS = [
#     ('csv', 'core.exporters.CSVExporterBOM'),
#     ('excel', 'explorer.exporters.ExcelExporter'),
#     ('json', 'explorer.exporters.JSONExporter')
# ]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = (
    ('en', _('English')),
    ('hu', _('Hungarian')),
)

# LOCALE_PATHS = ('/data/files/locale/',)
# MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
#
# # # ROSETTA
# # ROSETTA_MESSAGES_PER_PAGE = 50
# # CACHES = {
# #     'default': {
# #         'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
# #         'LOCATION': 'cache_table',
# #     }
# # }
#
# # DATE_FORMAT = ('Y-m-d')
# # DATETIME_FORMAT = ('Y-m-d H:i:s')
# # TIME_FORMAT = ('H:i:s')
#
# # File Upload max 50MB
# DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
# FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
FILE_UPLOAD_PERMISSIONS = 0o640

# LOGIN_REDIRECT_URL = '/'
# LOGOUT_REDIRECT_URL = '/'

# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

LOGGING_CONFIG = None
log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'django': {
            # 'class': 'core.logging.GStackFormatter',
            'format': '|{asctime}|{name}|{levelname}|{message}',
            'datefmt': '%Y-%m-%d %H:%M:%S%z',
            'style': '{',
        },
    },
    'handlers': {
        # 'console': {
        #     'level': 'INFO',
        #     'formatter': 'django',
        #     'class': 'logging.StreamHandler',
        # },
        "file": {
            'level': "DEBUG",
            "formatter": "django",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/host/log/django/django.log",
            "maxBytes": 2000,
            "backupCount": 10,
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    }
}

# if (
#     not DEBUG or
#     os.environ.get('MAIL_ADMINS_ON_ERROR_IN_DEBUG', '').lower() == 'true'
# ):
#     log_config['loggers']['django.request'] = {'handlers': ['mail_admins']}

logging.config.dictConfig(log_config)
