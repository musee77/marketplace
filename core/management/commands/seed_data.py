import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from accounts.forms import SignUpForm
from accounts.models import User, SpecialistProfile, ClientProfile
from services.models import Category, Service
from orders.models import Order
from reviews.models import Review
from blog.models import BlogCategory, BlogPost


CATEGORIES = [
    ("Business Intelligence & Dashboards", "chart"),
    ("Data Engineering & Pipelines", "pipeline"),
    ("Machine Learning & AI", "brain"),
    ("Statistical Analysis", "sigma"),
    ("Data Visualization", "eye"),
    ("Data Science Consulting", "compass"),
]

SPECIALISTS = [
    dict(email="dana@datahire.test", headline="Senior Data Engineer",
         skills="Python, Airflow, Spark, SQL, dbt", rate=70, years=7, loc="Berlin, DE",
         cat="Data Engineering & Pipelines", verified=True),
    dict(email="marco@datahire.test", headline="BI Developer & Dashboard Designer",
         skills="Power BI, Tableau, DAX, SQL", rate=55, years=5, loc="Milan, IT",
         cat="Business Intelligence & Dashboards", verified=True),
    dict(email="priya@datahire.test", headline="Statistical Analyst",
         skills="R, SPSS, Statistical Modeling, A/B Testing", rate=45, years=6, loc="Bengaluru, IN",
         cat="Statistical Analysis", verified=False),
    dict(email="jules@datahire.test", headline="Machine Learning Engineer",
         skills="Python, scikit-learn, TensorFlow, MLOps", rate=75, years=8, loc="Lyon, FR",
         cat="Machine Learning & AI", verified=True),
    dict(email="kenji@datahire.test", headline="Data Visualization Specialist",
         skills="D3.js, Plotly, Figma, Storytelling with Data", rate=58, years=5, loc="Osaka, JP",
         cat="Data Visualization", verified=False),
    dict(email="ana@datahire.test", headline="Data Science Consultant",
         skills="Python, SQL, Forecasting, Strategy", rate=80, years=9, loc="Lisbon, PT",
         cat="Data Science Consulting", verified=True),
]

CLIENTS = [
    dict(email="tomas@datahire.test", company="Acme Retail Co.", loc="Austin, US"),
    dict(email="sarah@datahire.test", company="Northwind Traders", loc="Toronto, CA"),
    dict(email="wei@datahire.test", company="Lumen Labs", loc="Singapore, SG"),
]

SERVICES_BY_EMAIL = {
    "dana@datahire.test": [
        ("Build a production-ready ETL/ELT pipeline", 900, 10,
         "I'll design and build an Airflow or dbt pipeline that ingests, cleans, and models your data reliably."),
        ("Migrate your data warehouse to Snowflake/BigQuery", 1200, 14,
         "Full migration plan, schema redesign, and a validated cutover from your legacy warehouse."),
    ],
    "marco@datahire.test": [
        ("Build an executive Power BI dashboard", 550, 8,
         "A Power BI dashboard connected to your data source with DAX measures and decision-ready visuals."),
        ("Redesign a cluttered Tableau workbook", 300, 5,
         "I'll audit and rebuild your Tableau dashboards for clarity, performance, and self-service filtering."),
    ],
    "priya@datahire.test": [
        ("Run an A/B test analysis with statistical rigor", 320, 6,
         "Full experiment design review, significance testing, and a plain-English readout for stakeholders."),
    ],
    "jules@datahire.test": [
        ("Build and deploy a churn prediction model", 1100, 12,
         "End-to-end ML pipeline: feature engineering, model selection, evaluation, and a deployable API."),
    ],
    "kenji@datahire.test": [
        ("Turn a messy dataset into a compelling visual story", 400, 6,
         "Interactive D3.js or Plotly visualizations designed to make your data's story obvious at a glance."),
    ],
    "ana@datahire.test": [
        ("Data strategy & analytics roadmap consulting", 850, 8,
         "A working session plus a written roadmap covering data maturity, tooling, and quick wins for your team."),
    ],
}

REQUIREMENTS = [
    "Need this for an internal tool used by our ops team, please keep it simple.",
    "This is for a client-facing launch next month, quality bar is high.",
    "Early-stage startup — happy to move fast and iterate.",
]

REVIEW_COMMENTS = [
    "Delivered exactly what we needed, ahead of schedule. Communication was excellent throughout.",
    "Solid work overall. A couple of revision rounds but the end result was worth it.",
    "Great to work with — asked the right questions up front and nailed the brief.",
]

BLOG_POSTS = [
    dict(
        title="From dashboards to decisions: a practical analytics workflow",
        slug="dashboards-to-decisions-analytics-workflow",
        excerpt="A simple way to move from reporting activity to decisions your team can act on.",
        content="""Good analytics starts with the decision, not the dashboard. Before choosing a chart or tool, write down what someone needs to decide and how often that decision happens.

Next, define the smallest useful set of metrics. A focused scorecard is easier to trust, maintain, and explain than a wall of numbers. Pair each metric with an owner and a clear action for when it changes.

Finally, build a feedback loop. Talk to the people using the analysis, remove what they do not need, and keep improving the path from signal to action.""",
        seo_title="A practical analytics workflow for better decisions",
        seo_description="Learn a simple analytics workflow that turns dashboards into focused, repeatable business decisions.",
    ),
    dict(
        title="How to choose the right data analytics specialist",
        slug="choose-the-right-data-analytics-specialist",
        excerpt="The questions that help you match a data project with the right specialist before work begins.",
        content="""The best specialist match depends on the decision your project needs to support. Start by describing the outcome in plain language, then identify the data sources, constraints, and delivery timeline.

Look for evidence of similar work rather than a long list of tools. Ask how the specialist validates assumptions, communicates uncertainty, and hands work over to your team.

A strong kickoff should end with a shared definition of done, a short plan, and an early checkpoint. That alignment is often more valuable than selecting a particular technology.""",
        seo_title="How to choose a data analytics specialist",
        seo_description="Use these practical questions to find the right data analytics specialist for your project and goals.",
    ),
    dict(
        title="Three ways to make a data project easier to trust",
        slug="make-a-data-project-easier-to-trust",
        excerpt="Trust grows when data work is transparent, testable, and connected to the decisions it supports.",
        content="""Trust is built into a data project through small, visible habits. First, document where important fields come from and what each transformation does. This gives reviewers something concrete to inspect.

Second, test the edges. Check missing values, unusual ranges, duplicate records, and changes in volume. Automated checks turn quiet data problems into visible work items.

Third, show the limits. Every analysis has assumptions and uncertainty. Naming them clearly helps stakeholders use the result well instead of treating it as a promise.""",
        seo_title="How to build trust in a data analytics project",
        seo_description="Three practical habits make analytics projects more transparent, testable, and trustworthy for stakeholders.",
    ),
    dict(
        title="A field guide to cleaning messy business data",
        slug="field-guide-cleaning-messy-business-data",
        excerpt="A repeatable approach for turning inconsistent source data into something your team can use with confidence.",
        content="""Messy data is usually a process problem before it is a technical problem. Start by listing the fields that matter to the decision and the rules each field should follow.

Standardize names, dates, categories, and units before trying to analyze the data. Keep the original values in a raw layer so that every correction can be traced and reviewed.

Then measure what changed. A short data-quality report showing missingness, duplicates, and invalid values gives stakeholders a shared view of progress and helps prevent the same issues from returning.""",
        seo_title="How to clean messy business data",
        seo_description="Follow a repeatable process for cleaning inconsistent business data and keeping improvements traceable.",
    ),
    dict(
        title="What makes a useful KPI",
        slug="what-makes-a-useful-kpi",
        excerpt="Good KPIs connect a team's actions to a meaningful outcome without hiding the details that explain change.",
        content="""A useful KPI answers three questions: what changed, why does it matter, and what can the team do next? If it only reports activity, it may be a useful measure but not a key performance indicator.

Define the population, time window, calculation, and owner. Those details should be easy to find beside the number rather than hidden in a separate document.

Review KPIs regularly. When a measure stops changing decisions, replace it with a better signal instead of collecting it forever.""",
        seo_title="What makes a KPI useful for a business",
        seo_description="Learn how to define KPIs that connect measurable change with meaningful business decisions and actions.",
    ),
    dict(
        title="SQL habits that keep analytics work maintainable",
        slug="sql-habits-for-maintainable-analytics",
        excerpt="Small SQL conventions can make shared models easier to review, debug, and safely extend.",
        content="""Maintainable SQL makes its assumptions visible. Use clear names, keep transformations in logical stages, and avoid repeating business rules in multiple queries.

Separate source cleanup from business logic. That makes it easier to test each layer and identify whether a problem began in the data or in the analysis.

Add simple checks for row counts, uniqueness, and accepted values. A query that runs successfully can still produce the wrong result, so correctness needs explicit tests.""",
        seo_title="SQL habits for maintainable analytics",
        seo_description="Use these practical SQL habits to make analytics models easier to review, test, and maintain.",
    ),
    dict(
        title="A calmer way to plan an analytics project",
        slug="calmer-way-to-plan-an-analytics-project",
        excerpt="A focused project brief gives analysts and stakeholders enough structure to move quickly without guessing.",
        content="""Begin with a one-sentence decision statement and a definition of done. Then list the data sources, known constraints, people who will use the result, and the date it needs to be useful.

Break the work into checkpoints that produce something reviewable. An early sketch of the output often reveals unclear requirements sooner than a polished final dashboard.

Leave room for discovery. Data projects rarely follow the first plan exactly, and a visible decision log helps everyone understand why the scope changed.""",
        seo_title="How to plan a better analytics project",
        seo_description="Plan analytics work with a focused brief, useful checkpoints, and enough room for data discovery.",
    ),
    dict(
        title="When to automate a recurring report",
        slug="when-to-automate-a-recurring-report",
        excerpt="Automation is valuable when it removes repeated effort without making an important judgment harder to see.",
        content="""Start by observing the current report for a few cycles. Record how long it takes, which steps are repeated, which inputs change, and where someone has to make a judgment.

Automate stable preparation steps first: collecting files, validating schemas, refreshing models, and distributing a consistent output. Keep decisions and exceptions visible to the people responsible for them.

Measure the result after launch. Time saved matters, but so do fewer errors, faster access, and a clearer record of how the numbers were produced.""",
        seo_title="When to automate a recurring data report",
        seo_description="Learn which parts of a recurring report to automate first and how to measure whether automation helps.",
    ),
    dict(
        title="How to communicate uncertainty in analytics",
        slug="communicate-uncertainty-in-analytics",
        excerpt="Clear uncertainty does not weaken an analysis; it helps people make decisions with the right level of confidence.",
        content="""Uncertainty becomes easier to understand when it is tied to the decision. Explain what could change the result, how large that effect might be, and what evidence would reduce the uncertainty.

Use ranges, scenarios, and plain language where they are more useful than a single precise-looking number. State which assumptions are strong, weak, or still untested.

Close with an action. A recommendation can be useful even when the evidence is incomplete if the next step is proportionate, reversible, and designed to teach the team more.""",
        seo_title="How to communicate uncertainty in analytics",
        seo_description="Explain assumptions, ranges, and confidence clearly so stakeholders can act responsibly on analytical results.",
    ),
    dict(
        title="The first 30 days of a data quality program",
        slug="first-30-days-of-a-data-quality-program",
        excerpt="A practical first month can establish ownership, visibility, and a short list of improvements that matter.",
        content="""In the first week, choose a small set of critical data elements and document where they come from. Speak with the people who create, transform, and use them.

During the next two weeks, add lightweight checks for freshness, completeness, uniqueness, and accepted values. Publish the results where owners can see them, and agree on what requires action.

Use the final week to prioritize fixes by decision impact. A quality program becomes sustainable when ownership and follow-up are part of normal work rather than a separate cleanup campaign.""",
        seo_title="Start a data quality program in 30 days",
        seo_description="A practical 30-day plan for improving data quality through ownership, visible checks, and focused fixes.",
    ),
]

BLOG_CATEGORIES = [
    ("Analytics strategy", "analytics-strategy"),
    ("Data quality", "data-quality"),
    ("Business intelligence", "business-intelligence"),
    ("Data engineering", "data-engineering"),
    ("Working with specialists", "working-with-specialists"),
]


def _create_via_form(email, role, password="specialistpass123"):
    """Create a user through SignUpForm so all signup logic is exercised."""
    if User.objects.filter(email=email).exists():
        return User.objects.get(email=email), False

    form = SignUpForm(data={
        "email": email,
        "role": role,
        "referral_code": "",
        "password": password,
    })
    if not form.is_valid():
        raise ValueError(f"SignUpForm invalid for {email}: {form.errors}")
    user = form.save()
    return user, True


class Command(BaseCommand):
    help = "Seed the database with demo users, services, orders, and reviews."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing demo data first")

    def handle(self, *args, **options):
        random.seed(7)

        if options["flush"]:
            Review.objects.all().delete()
            BlogPost.objects.all().delete()
            Order.objects.all().delete()
            Service.objects.all().delete()
            SpecialistProfile.objects.all().delete()
            ClientProfile.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.WARNING("Cleared existing demo data."))

        # --- manager (created directly — special role not in SignUpForm) ---
        manager, created = User.objects.get_or_create(
            username="ops_manager",
            defaults=dict(email="ops@datahire.test", role=User.Role.MANAGER),
        )
        if created:
            manager.set_password("managerpass123")
            manager.save()
            self.stdout.write(self.style.SUCCESS(f"Created manager: {manager.username} / managerpass123"))

        # --- blog posts ---
        blog_categories = [
            BlogCategory.objects.update_or_create(slug=slug, defaults={"name": name})[0]
            for name, slug in BLOG_CATEGORIES
        ]
        for post_data in BLOG_POSTS:
            post_index = BLOG_POSTS.index(post_data)
            BlogPost.objects.update_or_create(
                slug=post_data["slug"],
                defaults={
                    **post_data,
                    "category": blog_categories[post_index % len(blog_categories)],
                    "author": manager,
                    "status": BlogPost.Status.PUBLISHED,
                    "published_at": timezone.now() - timedelta(days=len(BLOG_POSTS) - post_index),
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Blog posts ready: {len(BLOG_POSTS)}"))

        # --- categories ---
        cat_objs = {}
        for name, icon in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name, defaults=dict(slug=slugify(name), icon=icon))
            cat_objs[name] = cat

        self.stdout.write(self.style.SUCCESS(f"Categories ready: {len(cat_objs)}"))

        # --- specialists (via SignUpForm) ---
        specialist_users = {}
        for s in SPECIALISTS:
            user, created = _create_via_form(s["email"], User.Role.SPECIALIST)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created specialist: {user.username} ({s['email']})"))
            profile = user.specialist_profile
            profile.headline = s["headline"]
            profile.bio = f"{s['headline']} with {s['years']} years of experience in {s['skills'].lower()}."
            profile.skills = s["skills"]
            profile.hourly_rate = s["rate"]
            profile.years_experience = s["years"]
            profile.location = s["loc"]
            profile.is_verified = s["verified"]
            profile.is_available = True
            profile.save()
            specialist_users[s["email"]] = (user, cat_objs[s["cat"]])
        self.stdout.write(self.style.SUCCESS(f"Specialists ready: {len(specialist_users)}"))

        # --- clients (via SignUpForm) ---
        client_users = {}
        for c in CLIENTS:
            user, created = _create_via_form(c["email"], User.Role.CLIENT, password="clientpass123")
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created client: {user.username} ({c['email']})"))
            profile = user.client_profile
            profile.company_name = c["company"]
            profile.location = c["loc"]
            profile.bio = f"{c['company']} hires specialists on DataHire for ongoing projects."
            profile.save()
            client_users[c["email"]] = user
        self.stdout.write(self.style.SUCCESS(f"Clients ready: {len(client_users)}"))

        # --- services ---
        all_services = []
        for email, listings in SERVICES_BY_EMAIL.items():
            user, category = specialist_users[email]
            for title, price, days, desc in listings:
                slug = slugify(title)
                service, _ = Service.objects.update_or_create(
                    slug=slug,
                    defaults=dict(specialist=user, category=category, title=title, description=desc,
                                  price=price, delivery_days=days, is_active=True),
                )
                all_services.append(service)
        self.stdout.write(self.style.SUCCESS(f"Services ready: {len(all_services)}"))

        # --- orders across every status, spread over the last 30 days ---
        statuses_cycle = [Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.IN_PROGRESS,
                           Order.Status.DELIVERED, Order.Status.COMPLETED, Order.Status.COMPLETED,
                           Order.Status.CANCELLED, Order.Status.DECLINED]
        client_list = list(client_users.values())
        created_orders = []
        Order.objects.all().delete()   # keep seeding idempotent for orders/reviews
        Review.objects.all().delete()

        order_index = 0
        for service in all_services:
            for _ in range(2):  # 2 orders per service
                status = statuses_cycle[order_index % len(statuses_cycle)]
                client = client_list[order_index % len(client_list)]
                days_ago = random.randint(1, 28)
                order = Order.objects.create(
                    service=service, client=client, specialist=service.specialist, status=status,
                    requirements=random.choice(REQUIREMENTS), price=service.price,
                    due_date=timezone.now().date() + timedelta(days=random.randint(3, 20)),
                )
                Order.objects.filter(pk=order.pk).update(
                    created_at=timezone.now() - timedelta(days=days_ago),
                    updated_at=timezone.now() - timedelta(days=max(days_ago - 1, 0)),
                )
                created_orders.append(order)
                order_index += 1

        self.stdout.write(self.style.SUCCESS(f"Orders created: {len(created_orders)}"))

        # --- reviews for completed orders ---
        review_count = 0
        for order in created_orders:
            order.refresh_from_db()
            if order.status == Order.Status.COMPLETED:
                Review.objects.create(
                    order=order, service=order.service, reviewer=order.client, reviewee=order.specialist,
                    rating=random.choice([4, 4, 5, 5, 5, 3]), comment=random.choice(REVIEW_COMMENTS),
                )
                review_count += 1
        self.stdout.write(self.style.SUCCESS(f"Reviews created: {review_count}"))

        self.stdout.write(self.style.SUCCESS(
            "\nDemo logins (all use password shown):\n"
            "  manager     -> ops@datahire.test     / managerpass123\n"
            "  specialists -> dana@datahire.test, marco@datahire.test, priya@datahire.test,\n"
            "                 jules@datahire.test, kenji@datahire.test, ana@datahire.test / specialistpass123\n"
            "  clients     -> tomas@datahire.test, sarah@datahire.test, wei@datahire.test / clientpass123\n"
        ))

