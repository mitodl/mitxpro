"""admin classes for ecommerce"""
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from ecommerce.models import (
    Line,
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
    ProductCouponAssignment,
)

from hubspot.task_helpers import sync_hubspot_deal
from mitxpro.admin import AuditableModelAdmin
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
        return queryset.filter(content_type__model=self.value())


class LineAdmin(admin.ModelAdmin):
    """Admin for Line"""

    model = Line
    list_display = ("id", "order", "get_product_version_text_id", "quantity")

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


class OrderAdmin(AuditableModelAdmin):
    """Admin for Order"""

    model = Order
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


class OrderAuditAdmin(admin.ModelAdmin):
    """Admin for OrderAudit"""

    model = OrderAudit
    readonly_fields = get_field_names(OrderAudit)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReceiptAdmin(admin.ModelAdmin):
    """Admin for Receipt"""

    model = Receipt
    readonly_fields = get_field_names(Receipt)

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


class CouponPaymentVersionAdmin(admin.ModelAdmin):
    """Admin for CouponPaymentVersions"""

    model = CouponPaymentVersion
    save_as = True
    save_as_continue = False
    save_on_top = True
    raw_id_fields = ("payment",)

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {"all": ("css/django-admin-version.css",)}


class CouponVersionAdmin(admin.ModelAdmin):
    """Admin for CouponVersions"""

    model = CouponVersion
    save_as = True
    save_as_continue = False
    save_on_top = True
    raw_id_fields = ("coupon", "payment_version")

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {"all": ("css/django-admin-version.css",)}


class CouponSelectionAdmin(admin.ModelAdmin):
    """Admin for CouponSelections"""

    model = CouponSelection
    raw_id_fields = ("coupon", "basket")


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
    list_display = ("id", "content_object")
    list_filter = ("is_active", ProductContentTypeListFilter)

    def get_queryset(self, request):
        """Return all active and in_active products"""
        return Product.all_objects


class DataConsentUserAdmin(admin.ModelAdmin):
    """Admin for DataConsentUser"""

    list_display = ("id", "user", "created_on")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user", "coupon")

    model = DataConsentUser


class DataConsentUserInline(admin.StackedInline):
    """Admin Inline for DataConsentUser objects"""

    model = DataConsentUser
    raw_id_fields = ("user", "coupon")
    extra = 1
    show_change_link = True


class DataConsentAgreementAdmin(admin.ModelAdmin):
    """Admin for DataConsentAgreement"""

    list_filter = ("company",)
    list_display = ("id", "company", "created_on")
    search_fields = ("company", "content")
    raw_id_fields = ("courses",)
    inlines = [DataConsentUserInline]

    model = DataConsentAgreement


class CompanyAdmin(admin.ModelAdmin):
    """Admin for Company"""

    model = Company


class ProductCouponAssignmentAdmin(admin.ModelAdmin):
    """Admin for ProductCouponAssignment"""

    list_display = ("id", "email", "get_coupon", "get_product")
    search_fields = (
        "email",
        "product_coupon__coupon__coupon_code",
        "product_coupon__coupon__payment__name",
    )
    raw_id_fields = ("product_coupon",)

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
admin.site.register(ProductCouponAssignment, ProductCouponAssignmentAdmin)
admin.site.register(Company, CompanyAdmin)
