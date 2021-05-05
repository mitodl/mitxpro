"""admin classes for ecommerce"""
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django import forms
from django.core.exceptions import ValidationError

from courses.models import Course
from ecommerce.models import (
    Line,
    LineRunSelection,
    ProgramRunLine,
    Order,
    OrderAudit,
    Receipt,
    Coupon,
    CouponVersion,
    CouponPaymentVersion,
    CouponPayment,
    CouponSelection,
    CouponEligibility,
    CouponRedemption,
    Product,
    ProductVersion,
    DataConsentAgreement,
    DataConsentUser,
    Company,
    BulkCouponAssignment,
    ProductCouponAssignment,
)

from hubspot.task_helpers import sync_hubspot_deal
from mitxpro.admin import AuditableModelAdmin, TimestampedModelAdmin
from mitxpro.utils import get_field_names


class ProductContentTypeListFilter(admin.SimpleListFilter):
    """Custom filter class for filtering ContentTypes and limiting the options to course run and program"""

    title = "content type"
    parameter_name = "content_type"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded value for the option that will
        appear in the URL query. The second element is the human-readable name for the option that will appear
        in the right sidebar.
        """
        valid_content_types = ContentType.objects.filter(
            model__in=["courserun", "program"]
        ).values_list("model", flat=True)
        return zip(valid_content_types, valid_content_types)

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query string and retrievable via
        `self.value()`.
        """
        qset_filter = {} if not self.value() else {"content_type__model": self.value()}
        return queryset.filter(**qset_filter)


class LineAdmin(admin.ModelAdmin):
    """Admin for Line"""

    model = Line
    list_display = ("id", "order", "get_product_version_text_id", "quantity")
    search_fields = ("order__id", "product_version__text_id")

    readonly_fields = get_field_names(Line)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_product_version_text_id(self, obj):
        """Returns the related ProductVersion text_id"""
        return obj.product_version.text_id

    get_product_version_text_id.short_description = "Product Object Text Id"
    get_product_version_text_id.admin_order_field = "product_version__text_id"


class LineRunSelectionAdmin(admin.ModelAdmin):
    """Admin for LineRunSelection"""

    model = LineRunSelection
    list_display = ("id", "line", "get_order", "get_run_courseware_id")
    readonly_fields = get_field_names(LineRunSelection)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_order(self, obj):
        """Returns the related Order"""
        return obj.line.order

    get_order.short_description = "Order"
    get_order.admin_order_field = "line__order"

    def get_run_courseware_id(self, obj):
        """Returns the courseware_id of the associated CourseRun"""
        return obj.run.courseware_id

    get_run_courseware_id.short_description = "Run Courseware Id"
    get_run_courseware_id.admin_order_field = "run__courseware_id"


class ProgramRunLineAdmin(admin.ModelAdmin):
    """Admin for ProgramRunLine"""

    model = ProgramRunLine
    list_display = ("id", "line", "get_order", "program_run")

    readonly_fields = get_field_names(ProgramRunLine)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_order(self, obj):
        """Returns the related Order"""
        return obj.line.order

    get_order.short_description = "Order"
    get_order.admin_order_field = "line__order"


class OrderAdmin(AuditableModelAdmin, TimestampedModelAdmin):
    """Admin for Order"""

    model = Order
    include_created_on_in_list = True
    list_filter = ("status",)
    list_display = ("id", "purchaser", "status", "created_on")
    search_fields = ("purchaser__username", "purchaser__email")

    readonly_fields = [name for name in get_field_names(Order) if name != "status"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        """
        Saves object and logs change to object
        """
        super().save_model(request, obj, form, change)
        sync_hubspot_deal(obj)


class OrderAuditAdmin(TimestampedModelAdmin):
    """Admin for OrderAudit"""

    model = OrderAudit
    include_created_on_in_list = True
    list_display = ("id", "order_id", "get_order_user")
    readonly_fields = get_field_names(OrderAudit)

    def get_order_user(self, obj):
        """Returns the related Order's user email"""
        return obj.order.purchaser.email

    get_order_user.short_description = "User"
    get_order_user.admin_order_field = "order__purchaser__email"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReceiptAdmin(TimestampedModelAdmin):
    """Admin for Receipt"""

    model = Receipt
    include_created_on_in_list = True
    list_display = ("id", "order_id", "get_order_user")
    readonly_fields = get_field_names(Receipt)
    ordering = ("-created_on",)

    def get_order_user(self, obj):
        """Returns the related Order's user email"""
        return obj.order.purchaser.email if obj.order is not None else None

    get_order_user.short_description = "User"
    get_order_user.admin_order_field = "order__purchaser__email"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CouponPaymentVersionInline(admin.StackedInline):
    """Admin Inline for CouponPaymentVersion objects"""

    model = CouponPaymentVersion
    readonly_fields = get_field_names(CouponPaymentVersion)
    extra = 0
    show_change_link = True
    can_delete = False
    ordering = ("-created_on",)
    min_num = 0


class CouponVersionInline(admin.StackedInline):
    """Admin Inline for CouponVersion objects"""

    model = CouponVersion
    readonly_fields = get_field_names(CouponVersion)
    raw_id_fields = ("coupon", "payment_version")
    extra = 0
    show_change_link = True
    can_delete = False
    ordering = ("-created_on",)
    min_num = 0


class CouponAdmin(admin.ModelAdmin):
    """Admin for Coupons"""

    list_display = ("id", "coupon_code", "get_payment_name")
    search_fields = ("coupon_code", "payment__name")
    list_filter = ("payment",)
    raw_id_fields = ("payment",)

    model = Coupon
    save_on_top = True
    inlines = [CouponVersionInline]

    def get_queryset(self, request):
        """Overrides base queryset"""
        return super().get_queryset(request).select_related("payment")

    def get_payment_name(self, obj):
        """Returns the related CouponPayment name"""
        return obj.payment.name

    get_payment_name.short_description = "Coupon Payment Name"
    get_payment_name.admin_order_field = "payment__name"


class CouponPaymentAdmin(admin.ModelAdmin):
    """Admin for CouponPayments"""

    model = CouponPayment
    save_on_top = True
    inlines = [CouponPaymentVersionInline]
    list_display = ("id", "name")
    search_fields = ("name",)


class CouponPaymentVersionAdmin(admin.ModelAdmin):
    """Admin for CouponPaymentVersions"""

    model = CouponPaymentVersion
    save_as = True
    save_as_continue = False
    save_on_top = True
    list_display = (
        "id",
        "get_payment_name",
        "get_company_name",
        "payment_type",
        "amount",
        "num_coupon_codes",
        "activation_date",
        "max_redemptions_per_user",
    )
    raw_id_fields = ("payment",)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_payment_name(self, obj):
        """Returns the related CouponPayment name"""
        return obj.payment.name

    get_payment_name.short_description = "Coupon Payment Name"
    get_payment_name.admin_order_field = "payment__name"

    def get_company_name(self, obj):
        """Returns the related Company name"""
        return None if not obj.company else obj.company.name

    get_company_name.short_description = "Company Name"

    class Media:
        css = {"all": ("css/django-admin-version.css",)}


class CouponVersionAdmin(admin.ModelAdmin):
    """Admin for CouponVersions"""

    model = CouponVersion
    save_as = True
    save_as_continue = False
    save_on_top = True
    list_display = ("id", "get_coupon_code", "get_payment_name")
    raw_id_fields = ("coupon", "payment_version")

    def has_delete_permission(self, request, obj=None):
        return False

    def get_coupon_code(self, obj):
        """Returns the related Coupon code"""
        return obj.coupon.coupon_code

    get_coupon_code.short_description = "Coupon Code"
    get_coupon_code.admin_order_field = "coupon__coupon_code"

    def get_payment_name(self, obj):
        """Returns the related CouponPayment name"""
        return obj.payment_version.payment.name

    get_payment_name.short_description = "Coupon Payment Name"
    get_payment_name.admin_order_field = "payment__name"

    class Media:
        css = {"all": ("css/django-admin-version.css",)}


class CouponSelectionAdmin(admin.ModelAdmin):
    """Admin for CouponSelections"""

    model = CouponSelection
    list_display = ("id", "get_payment_name", "get_coupon_code", "get_basket_user")
    raw_id_fields = ("coupon", "basket")

    def get_payment_name(self, obj):
        """Returns the related CouponPayment name"""
        return obj.coupon.payment.name

    get_payment_name.short_description = "Coupon Payment Name"
    get_payment_name.admin_order_field = "coupon__payment__name"

    def get_coupon_code(self, obj):
        """Returns the related Coupon code"""
        return obj.coupon.coupon_code

    get_coupon_code.short_description = "Coupon Code"
    get_coupon_code.admin_order_field = "coupon__coupon_code"

    def get_basket_user(self, obj):
        """Returns the related Basket user's email"""
        return obj.basket.user.email

    get_basket_user.short_description = "Basket User"
    get_basket_user.admin_order_field = "basket__user__email"


class CouponEligibilityAdmin(admin.ModelAdmin):
    """Admin for CouponEligibilitys"""

    list_display = ("id", "coupon", "product")
    search_fields = ("coupon__coupon_code", "coupon__payment__name")
    list_filter = ("product",)
    raw_id_fields = ("coupon", "product")

    model = CouponEligibility

    def get_product_text_id(self, obj):
        """Returns the text id of the related Product object"""
        return obj.product.content_object.text_id

    get_product_text_id.short_description = "Product Object Text ID"
    get_product_text_id.admin_order_field = "product__content_object__text_id"


class CouponRedemptionAdmin(admin.ModelAdmin):
    """Admin for CouponRedemptions"""

    model = CouponRedemption
    list_display = (
        "id",
        "coupon_version_id",
        "order",
        "get_coupon_code",
        "get_coupon_payment_version",
    )
    raw_id_fields = ("coupon_version", "order")

    def get_queryset(self, request):
        """Return all active and in_active products"""
        return self.model.objects.get_queryset().select_related(
            "coupon_version__coupon"
        )

    def get_coupon_code(self, obj):
        """Returns the related Coupon"""
        return obj.coupon_version.coupon.coupon_code

    get_coupon_code.short_description = "Coupon Code"
    get_coupon_code.admin_order_field = "coupon_version__coupon__coupon_code"

    def get_coupon_payment_version(self, obj):
        """Returns the related Coupon"""
        return obj.coupon_version.payment_version

    get_coupon_payment_version.short_description = "Coupon Payment Version"
    get_coupon_payment_version.admin_order_field = "coupon_version__payment_version"


class ProductVersionAdmin(admin.ModelAdmin):
    """Admin for ProductVersion"""

    model = ProductVersion
    list_display = ("id", "product_id", "text_id", "price", "description")
    save_as = True
    save_as_continue = False
    save_on_top = True
    readonly_fields = ("text_id",)
    raw_id_fields = ("product",)
    search_fields = (
        "text_id",
        "description",
        "product__courseruns__title",
        "product__programs__title",
        "product__courseruns__courseware_id",
        "product__programs__readable_id",
    )

    def get_queryset(self, request):
        """Return all active and in_active products"""
        return self.model.objects.get_queryset().select_related("product")

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {"all": ("css/django-admin-version.css",)}


class ProductVersionInline(admin.StackedInline):
    """Inline form for ProductVersion"""

    model = ProductVersion
    readonly_fields = get_field_names(ProductVersion)
    extra = 0
    show_change_link = True
    can_delete = False
    ordering = ("-created_on",)
    min_num = 0


class ProductAdmin(admin.ModelAdmin):
    """Admin for Product"""

    model = Product
    inlines = [ProductVersionInline]
    list_display = ("id", "content_object", "get_text_id", "get_price")
    list_filter = ("is_active", ProductContentTypeListFilter)
    search_fields = (
        "courseruns__title",
        "programs__title",
        "courseruns__courseware_id",
        "programs__readable_id",
    )

    def get_text_id(self, obj):
        """Return the text id"""
        if obj.latest_version:
            return obj.latest_version.text_id

    def get_price(self, obj):
        """Return the price"""
        if obj.latest_version:
            return obj.latest_version.price

    def get_queryset(self, request):
        """Return all active and in_active products"""
        return Product.all_objects

    get_text_id.short_description = "Text ID"
    get_price.short_description = "Price"


class DataConsentUserAdmin(TimestampedModelAdmin):
    """Admin for DataConsentUser"""

    include_created_on_in_list = True
    list_display = ("id", "user")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user", "coupon")

    model = DataConsentUser


class DataConsentAgreementForm(forms.ModelForm):
    """Form for DataConsentAgreementAdmin"""

    class Meta:
        model = DataConsentAgreement
        fields = "__all__"

    def clean(self):
        is_global = self.cleaned_data.get("is_global", False)
        courses = self.cleaned_data.get("courses", Course.objects.none())
        company = self.cleaned_data.get("company", None)
        check_duplicate = self.instance.pk is None or self.instance.company != company
        # Check if a global agreement for a specific company already exists.
        # (Only applicable if a new object is created or company is changed in an existing object)
        if (
            check_duplicate
            and is_global
            and DataConsentAgreement.objects.filter(
                company=company, is_global=True
            ).exists()
        ):
            raise ValidationError(
                "You already have a global agreement for this company"
            )
        # Check that is_global flag is enabled or at least one course is associated with the agreement
        if not is_global and not courses.all():
            raise ValidationError(
                "You must either check All Courses box or select courses for the agreement"
            )
        # If is_global flag is true, we will just clean the associated course list
        if is_global:
            self.cleaned_data["courses"] = Course.objects.none()
        return self.cleaned_data


class DataConsentAgreementAdmin(TimestampedModelAdmin):
    """Admin for DataConsentAgreement"""

    include_created_on_in_list = True
    list_filter = ("company",)
    list_display = ("id", "company")
    search_fields = ("company", "content")
    raw_id_fields = ("courses",)

    form = DataConsentAgreementForm


class CompanyAdmin(admin.ModelAdmin):
    """Admin for Company"""

    model = Company


class BulkCouponAssignmentAdmin(TimestampedModelAdmin):
    """Admin for BulkCouponAssignment"""

    include_created_on_in_list = True
    list_display = (
        "id",
        "assignment_sheet_id",
        "assignments_started_date",
        "message_delivery_completed_date",
    )
    search_fields = ("assignment_sheet_id",)

    model = BulkCouponAssignment


class ProductCouponAssignmentAdmin(admin.ModelAdmin):
    """Admin for ProductCouponAssignment"""

    list_display = ("id", "email", "get_coupon", "get_product", "bulk_assignment_id")
    search_fields = (
        "email",
        "product_coupon__coupon__coupon_code",
        "product_coupon__coupon__payment__name",
    )
    raw_id_fields = ("product_coupon", "bulk_assignment")

    model = ProductCouponAssignment

    def get_queryset(self, request):
        """Overrides base queryset"""
        return (
            super()
            .get_queryset(request)
            .select_related("product_coupon__coupon", "product_coupon__product")
        )

    def get_coupon(self, obj):
        """Returns the related Coupon"""
        return obj.product_coupon.coupon

    get_coupon.short_description = "Coupon"
    get_coupon.admin_order_field = "product_coupon__coupon"

    def get_product(self, obj):
        """Returns the related Product object"""
        return obj.product_coupon.product

    get_product.short_description = "Product"
    get_product.admin_order_field = "product_coupon__product"


admin.site.register(Line, LineAdmin)
admin.site.register(LineRunSelection, LineRunSelectionAdmin)
admin.site.register(ProgramRunLine, ProgramRunLineAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderAudit, OrderAuditAdmin)
admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVersion, ProductVersionAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(CouponVersion, CouponVersionAdmin)
admin.site.register(CouponPayment, CouponPaymentAdmin)
admin.site.register(CouponPaymentVersion, CouponPaymentVersionAdmin)
admin.site.register(CouponSelection, CouponSelectionAdmin)
admin.site.register(CouponEligibility, CouponEligibilityAdmin)
admin.site.register(CouponRedemption, CouponRedemptionAdmin)
admin.site.register(DataConsentAgreement, DataConsentAgreementAdmin)
admin.site.register(DataConsentUser, DataConsentUserAdmin)
admin.site.register(BulkCouponAssignment, BulkCouponAssignmentAdmin)
admin.site.register(ProductCouponAssignment, ProductCouponAssignmentAdmin)
admin.site.register(Company, CompanyAdmin)
