from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from services.models import Service
from accounts.models import SpecialistProfile


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return ['core:home', 'core:about', 'services:list', 'blog:list']

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == 'core:about' else 0.8


class ServiceSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return Service.objects.filter(is_active=True, specialist__specialist_profile__is_approved=True).select_related('specialist', 'category')

    def lastmod(self, obj):
        return obj.updated_at


class SpecialistSitemap(Sitemap):
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return SpecialistProfile.objects.filter(is_approved=True).select_related('user')

    def lastmod(self, obj):
        return obj.updated_at
