from django import forms
from django.utils.text import slugify
from .models import Service, Category


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["title", "category", "description", "price", "delivery_days", "cover_image", "is_active"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base = slugify(instance.title)
            slug = base
            i = 1
            while Service.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            instance.slug = slug
        if commit:
            instance.save()
        return instance
