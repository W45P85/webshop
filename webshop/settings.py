
from pathlib import Path
from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-$sg+2ao_9&#$dqmz2#zin^&@!4pi-5s5e)=hh%2ga!%oxm1926"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # my apps
    'shop.apps.ShopConfig',
    
    # third party apps
    'paypal.standard.ipn',
    'star_ratings',
    'cookiebanner',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "webshop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                #"django.core.context_processors.request",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shop.context_processors.cart_count",
                "shop.context_processors.customer_profile",
            ],
        },
    },
]

WSGI_APPLICATION = "webshop.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "de-de"

TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

MEDIA_URL = "/img/"

MEDIA_ROOT = BASE_DIR / "static/img"

# Paypal
PAYPAL_TEST = True

# Ratings
STAR_RATINGS_RERATE = False
STAR_RATINGS_CLEARABLE = False

COOKIEBANNER = {
    "title": _("Cookie Einstellungen"),
    "header_text": _("Wir verwenden Cookies auf dieser Website. Einige sind unerlässlich, andere nicht."),
    "footer_text": _("Bitte akzeptieren Sie unsere Cookies."),
    "footer_links": [
        {"title": _("Impressum"), "href": "/imprint"},
        {"title": _("Datenschutz"), "href": "/privacy"},
    ],
    "groups": [
        {
            "id": "essential",
            "name": _("Essential"),
            "description": _("Unverzichtbare Cookies ermöglichen das Funktionieren dieser Seite."),
            "cookies": [
                {
                    "pattern": "cookiebanner",
                    "description": _("Meta-Cookie für die Cookies, die gesetzt werden."),
                },
                {
                    "pattern": "csrftoken",
                    "description": _("Dieses Cookie verhindert Cross-Site-Request-Forgery-Angriffe."),
                },
                {
                    "pattern": "sessionid",
                    "description": _("Dieses Cookie ist notwendig, um z.B. das Einloggen zu ermöglichen."),
                },
            ],
        },
        {
            "id": "analytics",
            "name": _("Analysen"),
            "optional": True,
            "cookies": [
                {
                    "pattern": "_pk_.*",
                    "description": _("Cookie für die Website-Analyse."),
                },
            ],
        },
    ],
}
