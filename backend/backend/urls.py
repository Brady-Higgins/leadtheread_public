
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler404
from . import views
import os
from dotenv import load_dotenv
from pathlib import Path

current_directory = Path.cwd()
dotenv_path = current_directory.parent / '.env'
load_dotenv(dotenv_path=dotenv_path, override=True)

urlpatterns = [
    path(f"{os.getenv('ADMIN_SITE_URL')}/", admin.site.urls),
    path('', views.homepage, name='homepage'),
    path('book_search/', views.book_search, name='book_search'),
    path('users/', include('users.urls'))
]

handler404 = views.custom_404_view