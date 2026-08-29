from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment", "image"]
        widgets = {
            "rating": forms.Select(choices=[(i, f"{i} star{'s' if i != 1 else ''}") for i in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "Share your experience working with this specialist on the deliverable..."}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }
        labels = {
            "image": "Attach Work Sample / Screenshot (Optional)",
        }
