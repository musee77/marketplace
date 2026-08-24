import bleach
import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({
    "h2", "h3", "h4", "p", "br", "hr", "blockquote",
    "pre", "code", "ul", "ol", "li", "strong", "em", "del",
    "a",
})
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "rel"]}
ALLOWED_PROTOCOLS = {"http", "https", "mailto"}


@register.filter
def blog_markdown(value):
    if not value:
        return ""
    rendered = markdown.markdown(
        str(value),
        extensions=["extra", "sane_lists", "nl2br"],
    )
    cleaned = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return mark_safe(cleaned)
