"""
Django settings for recipe project.
"""

import os
from pathlib import Path
import dj_database_url
import environ
from dotenv import load_dotenv

# ================================================
# 基本設定
# ================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# .env読み込み（ローカル開発時のみ）
load_dotenv()

# ✅ environ初期化（Render含む全環境で利用）
env = environ.Env(
    DEBUG=(bool, False)
)

# .envファイルが存在すれば読み込む
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)

# ================================================
# セキュリティ設定
# ================================================
SECRET_KEY = env('GEMINI_SECRET_KEY', default='django-insecure-y%v03-qg5)5l0r=s9*v_021q*0e80*+c=bd8cyb*0wl-t6(mkv')

DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# ================================================
# アプリケーション
# ================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ingredients',
    'rest_framework',
    'recipe',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ Whitenoiseは上に移動
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'recipe.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'recipe.wsgi.application'

# ================================================
# データベース設定
# ================================================
if DEBUG:
    # ローカル用
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Renderなど本番用
    DATABASES = {
        'default': dj_database_url.config(
            default=env('DATABASE_URL', default='postgresql://postgres:postgres@localhost:5432/recipeproject'),
            conn_max_age=600,
            ssl_require=True
        )
    }

# ================================================
# その他設定
# ================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
