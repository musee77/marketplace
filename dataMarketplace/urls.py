from django.urls import include, path, re_path
from django.contrib import admin as default_admin
from .admin import custom_admin_site
from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from core.sitemaps import StaticViewSitemap, ServiceSitemap, SpecialistSitemap
from blog.sitemaps import BlogPostSitemap
from core.file_responses import serve_media

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

urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve_media)]