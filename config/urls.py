from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from core.file_responses import serve_media

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('services/', include('services.urls')),
    path('orders/', include('orders.urls')),
    path('reviews/', include('reviews.urls')),
    path('api/', include('config.api_urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve_media)]
