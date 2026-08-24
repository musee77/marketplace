from django.urls import path, include
from django.contrib import admin as default_admin
from .admin import custom_admin_site
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from core.sitemaps import StaticViewSitemap, ServiceSitemap, SpecialistSitemap
from blog.sitemaps import BlogPostSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'services': ServiceSitemap,
    'specialists': SpecialistSitemap,
    'blog': BlogPostSitemap,
}

urlpatterns = [
    path('system/admin/', include('custom_admin.urls')),
    path('accounts/', include('accounts.urls')),
    path('services/', include('services.urls')),
    path('blog/', include('blog.urls')),
    path('orders/', include('orders.urls')),
    path('reviews/', include('reviews.urls')),
    path('chat/', include('chat.urls')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('api/', include('config.api_urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)