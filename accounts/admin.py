from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, SpecialistProfile, ClientProfile, SpecialistTest,
    SpecialistTestQuestion, SpecialistTestAttempt,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "referral_code", "referred_by", "referral_count", "is_suspended", "date_created")
    list_filter = ("role", "is_suspended", "is_staff")
    search_fields = ("username", "email", "referral_code")
    fieldsets = UserAdmin.fieldsets + (
        ("Marketplace", {"fields": ("role", "phone", "avatar", "is_suspended")}),
        ("Referral Program", {"fields": ("referral_code", "referred_by")}),
    )


from django.utils.html import format_html
from django.urls import reverse


@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "headline", "hourly_rate", "is_approved", "is_verified", "is_available", "quick_actions")
    list_filter = ("is_approved", "is_verified", "is_available")
    list_editable = ("is_verified",)
    search_fields = ("user__username", "headline", "skills")
    actions = ["approve_specialists", "reject_specialists"]

    @admin.display(description="Quick Approval")
    def quick_actions(self, obj):
        if not obj.is_approved:
            url = reverse("datahire_admin:approve_specialist", args=[obj.pk])
            return format_html(
                '<a class="button" style="background:#10b981;color:#fff;padding:5px 10px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;white-space:nowrap;" href="{}">✓ Approve</a>',
                url
            )
        else:
            revoke_url = reverse("datahire_admin:reject_specialist", args=[obj.pk])
            return format_html(
                '<span style="color:#10b981;font-weight:600;">✓ Approved</span> &nbsp;'
                '<a class="button" style="background:#ef4444;color:#fff;padding:3px 7px;font-size:0.75rem;border-radius:4px;text-decoration:none;display:inline-block;white-space:nowrap;" href="{}">Revoke</a>',
                revoke_url
            )

    @admin.action(description="Approve selected specialists")
    def approve_specialists(self, request, queryset):
        approved = 0
        blocked = 0
        for profile in queryset:
            if profile.missing_required_tests():
                blocked += 1
                continue
            profile.is_approved = True
            profile.approval_status = SpecialistProfile.ApprovalStatus.APPROVED
            profile.save(update_fields=("is_approved", "approval_status"))
            approved += 1
        self.message_user(request, f"{approved} specialist(s) approved; {blocked} blocked until tests are completed and approved.")

    def save_model(self, request, obj, form, change):
        if obj.is_approved and obj.missing_required_tests():
            obj.is_approved = False
            obj.approval_status = SpecialistProfile.ApprovalStatus.PENDING
            self.message_user(request, "Approval blocked until every active test has a completed, manager-approved response.", level="error")
        super().save_model(request, obj, form, change)

    @admin.action(description="Reject (unapprove) selected specialists")
    def reject_specialists(self, request, queryset):
        updated = queryset.update(
            is_approved=False,
            approval_status=SpecialistProfile.ApprovalStatus.REJECTED,
        )
        self.message_user(request, f"{updated} specialist(s) rejected.")


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "location", "balance", "default_payment_method")
    list_filter = ("default_payment_method",)
    search_fields = ("user__username", "user__email", "company_name", "location")
    fieldsets = (
        ("Client Profile", {"fields": ("user", "company_name", "bio", "location")}),
        ("Billing", {"fields": ("billing_address", "default_payment_method")}),
        ("Financials", {
            "fields": ("balance",),
            "description": "Edit the client's available account balance. Use a positive amount to allow balance payments.",
        }),
        ("Record", {"fields": ("created_at",), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at",)


class SpecialistTestQuestionInline(admin.TabularInline):
    model = SpecialistTestQuestion
    extra = 1


@admin.register(SpecialistTest)
class SpecialistTestAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "question_count", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "description")
    inlines = (SpecialistTestQuestionInline,)

    @admin.display(description="Questions")
    def question_count(self, obj):
        return obj.questions.count()


@admin.register(SpecialistTestAttempt)
class SpecialistTestAttemptAdmin(admin.ModelAdmin):
    list_display = ("specialist", "test", "score_display", "status", "submitted_at", "reviewed_by")
    list_filter = ("status", "test")
    search_fields = ("specialist__username", "specialist__email", "test__title")
    readonly_fields = ("specialist", "test", "score", "total_questions", "submitted_at")
    actions = ("approve_attempts", "reject_attempts")

    @admin.display(description="Score")
    def score_display(self, obj):
        return f"{obj.score}/{obj.total_questions} ({obj.percentage}%)"

    @admin.action(description="Accept selected test attempts")
    def approve_attempts(self, request, queryset):
        from django.utils import timezone
        approved = 0
        blocked = 0
        for attempt in queryset.prefetch_related("test__questions"):
            questions = list(attempt.test.questions.all())
            has_all_responses = all(
                attempt.responses.get(str(question.pk), "")
                for question in questions
            )
            if not questions or attempt.total_questions != len(questions) or not has_all_responses:
                blocked += 1
                continue
            attempt.status = SpecialistTestAttempt.Status.ACCEPTED
            attempt.reviewed_by = request.user
            attempt.reviewed_at = timezone.now()
            attempt.save(update_fields=("status", "reviewed_by", "reviewed_at"))
            attempt.specialist.specialist_profile.approve_after_assessments()
            approved += 1
        self.message_user(request, f"{approved} test attempt(s) accepted; {blocked} blocked because responses are incomplete.")

    @admin.action(description="Reject selected test attempts")
    def reject_attempts(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status=SpecialistTestAttempt.Status.REJECTED, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{updated} test attempt(s) rejected.")
