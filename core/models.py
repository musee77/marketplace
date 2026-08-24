from django.db import models

class SearchKeyword(models.Model):
    keyword = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True, help_text="Display on the homepage.")
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which keywords are shown.")

    class Meta:
        ordering = ["display_order", "keyword"]

    def __str__(self):
        return self.keyword
