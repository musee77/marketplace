from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BlogCategory, BlogPost
from accounts.models import User


class BlogPublicViewsTests(TestCase):
    def test_published_post_gets_publication_time_automatically(self):
        post = BlogPost.objects.create(
            title="Automatically published",
            slug="automatically-published",
            excerpt="Published now.",
            content="This post is live.",
            status=BlogPost.Status.PUBLISHED,
        )

        self.assertIsNotNone(post.published_at)
        self.assertLessEqual(post.published_at, timezone.now())

    def test_list_is_public_and_links_from_updates_menu(self):
        response = self.client.get(reverse("blog:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics insights")
        self.assertContains(response, 'href="/blog/"')

    def test_drafts_are_not_public(self):
        post = BlogPost.objects.create(
            title="Private draft",
            slug="private-draft",
            excerpt="Not ready for publication.",
            content="Draft content.",
        )

        response = self.client.get(post.get_absolute_url())

        self.assertEqual(response.status_code, 404)

    def test_published_post_renders_seo_metadata(self):
        post = BlogPost.objects.create(
            title="Choosing a better metric",
            slug="choosing-a-better-metric",
            excerpt="A practical guide to useful metrics.",
            content="Start with the decision you need to make.",
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(minutes=1),
            seo_title="Better metrics for analytics teams",
            seo_description="Learn how to choose metrics that support better decisions.",
        )

        response = self.client.get(post.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Better metrics for analytics teams")
        self.assertContains(response, '"@type": "BlogPosting"')
        self.assertContains(response, 'rel="canonical"')

    def test_search_and_category_filters_limit_results(self):
        category = BlogCategory.objects.create(name="Data quality", slug="data-quality")
        BlogPost.objects.create(
            title="Quality checks that scale",
            slug="quality-checks-that-scale",
            excerpt="Checks for reliable data.",
            content="Freshness and completeness checks.",
            category=category,
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(minutes=1),
        )
        BlogPost.objects.create(
            title="A dashboard review",
            slug="a-dashboard-review",
            excerpt="A better reporting workflow.",
            content="Review the decision first.",
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.get(reverse("blog:list"), {"q": "quality", "category": category.slug})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "Quality checks that scale")
        self.assertNotContains(response, "A dashboard review")

    def test_list_paginates_six_posts_per_page(self):
        for index in range(7):
            BlogPost.objects.create(
                title=f"Published article {index}",
                slug=f"published-article-{index}",
                excerpt="A published article.",
                content="Article content.",
                status=BlogPost.Status.PUBLISHED,
                published_at=timezone.now() - timedelta(minutes=1),
            )

        response = self.client.get(reverse("blog:list"))

        self.assertEqual(response.context["page_obj"].paginator.per_page, 6)
        self.assertEqual(len(response.context["page_obj"].object_list), 6)


class BlogAdminViewsTests(TestCase):
    def test_blog_admin_requires_manager(self):
        response = self.client.get(reverse("custom_admin:blog_list"))

        self.assertRedirects(response, "/admin/login/?next=/admin/blog/")

    def test_manager_can_open_blog_admin(self):
        manager = User.objects.create_user(
            username="blog_manager",
            email="blog-manager@example.com",
            password="manager-pass-123",
            role=User.Role.MANAGER,
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("custom_admin:blog_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blog posts")
        self.assertContains(response, "New post")

    def test_blog_admin_paginates_ten_posts_per_page(self):
        manager = User.objects.create_user(
            username="pagination_manager",
            email="pagination-manager@example.com",
            password="manager-pass-123",
            role=User.Role.MANAGER,
        )
        for index in range(11):
            BlogPost.objects.create(
                title=f"Admin article {index}",
                slug=f"admin-article-{index}",
                excerpt="An admin article.",
                content="Article content.",
            )
        self.client.force_login(manager)

        response = self.client.get(reverse("custom_admin:blog_list"))

        self.assertEqual(response.context["page_obj"].paginator.per_page, 10)
        self.assertEqual(len(response.context["page_obj"].object_list), 10)
        self.assertTrue(response.context["page_obj"].has_next())
