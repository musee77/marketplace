from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import BlogCategory, BlogPost


def post_list(request):
    posts = BlogPost.objects.published().select_related("author", "category")
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    current_category = BlogCategory.objects.filter(slug=category_slug).first() if category_slug else None
    if query:
        posts = posts.filter(
            Q(title__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(content__icontains=query)
        )
    if current_category:
        posts = posts.filter(category=current_category)
    page_obj = Paginator(posts, 6).get_page(request.GET.get("page"))
    return render(request, "blog/post_list.html", {
        "page_obj": page_obj,
        "categories": BlogCategory.objects.all(),
        "query": query,
        "category_slug": category_slug,
        "current_category": current_category,
    })


def post_detail(request, slug):
    post = get_object_or_404(
        BlogPost.objects.published().select_related("author", "category"),
        slug=slug,
    )
    return render(request, "blog/post_detail.html", {"post": post})
