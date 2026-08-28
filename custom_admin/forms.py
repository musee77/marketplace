from django import forms
from services.models import Category, Service
from accounts.models import User
from blog.models import BlogPost
from decimal import Decimal

class AdminServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['title', 'slug', 'specialist', 'category', 'description', 'price', 'delivery_days', 'cover_image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'specialist': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Data Visualization'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. data-visualization'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 📊 or chart-bar'}),
        }

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'role', 'is_suspended']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_suspended': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class BalanceForm(forms.Form):
    ACTION_CHOICES = (
        ('credit', 'Credit (Add funds)'),
        ('debit', 'Debit (Deduct funds)'),
        ('set', 'Set absolute balance'),
    )
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'), widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}))


class BlogPostForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control blog-content-editor', 'rows': 18}),
        help_text='Use Markdown: ## headings, **bold**, *italic*, - lists, and [links](https://example.com).',
    )

    class Meta:
        model = BlogPost
        fields = ['title', 'slug', 'category', 'excerpt', 'content', 'cover_image', 'status', 'seo_title', 'seo_description', 'canonical_url']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'excerpt': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'seo_title': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 60}),
            'seo_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': 160}),
            'canonical_url': forms.URLInput(attrs={'class': 'form-control'}),
        }
