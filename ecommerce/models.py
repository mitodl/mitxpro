"""Models for ecommerce"""
import logging

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.templatetags.static import static
from django.utils.functional import cached_property

from courses.constants import DEFAULT_COURSE_IMG_PATH
from ecommerce.constants import REFERENCE_NUMBER_PREFIX, ORDERED_VERSIONS_QSET_ATTR
from ecommerce.utils import get_order_id_by_reference_number
from mitxpro.models import (
    AuditableModel,
    AuditModel,
    TimestampedModel,
    PrefetchGenericQuerySet,
)
from mitxpro.utils import serialize_model_object, first_or_none
from mail.constants import MAILGUN_EVENT_CHOICES

log = logging.getLogger()


class Company(TimestampedModel):
    """
    A company that purchases bulk seats/coupons
    """

    name = models.CharField(max_length=512, unique=True)

    def __str__(self):
        """Description for Company"""
        return f"Company {self.name}"


class ProductQuerySet(PrefetchGenericQuerySet):  # pylint: disable=missing-docstring
    def active(self):
        """Filters for active products only"""
        return self.filter(is_active=True)

    def with_ordered_versions(self):
        """Prefetches related ProductVersions in reverse creation order"""
        return self.prefetch_related(
            models.Prefetch(
                "productversions",
                queryset=ProductVersion.objects.order_by("-created_on"),
                to_attr=ORDERED_VERSIONS_QSET_ATTR,
            )
        )


class _ProductManager(models.Manager):  # pylint: disable=missing-docstring
    def get_queryset(self):
        """Use the custom queryset, and filter by active products by default"""
        return ProductQuerySet(self.model, using=self._db).active()


ProductManager = _ProductManager.from_queryset(ProductQuerySet)


class Product(TimestampedModel):
    """
    Representation of a purchasable product. There is a GenericForeignKey to a Course or Program.
    Other about the product like price is stored in ProductVersion.
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        null=True,
        help_text="content_object is a link to either a CourseRun or a Program",
    )
    object_id = models.PositiveIntegerField()
    is_active = models.BooleanField(
        default=True,
        null=False,
        help_text="If it is unchecked then users will not be "
        "able to load the product on the checkout page.",
    )
    visible_in_bulk_form = models.BooleanField(
        default=True,
        null=False,
        help_text="If it is unchecked then this product will not be listed in the "
        "product drop-down on the bulk purchase form at /ecommerce/bulk.",
    )
    content_object = GenericForeignKey("content_type", "object_id")
    objects = ProductManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("content_type", "object_id")

    @cached_property
    def ordered_versions(self):
        """Return the list of product versions ordered by creation date descending"""
        return self.productversions.order_by("-created_on")

    @cached_property
    def latest_version(self):
        """Gets the most recently created ProductVersion associated with this Product"""
        return first_or_none(self.ordered_versions)

    @property
    def run_queryset(self):
        """Get a queryset for the runs related to the the product"""
        from courses.models import CourseRun

        if self.content_type.model == "courserun":
            # This looks strange since we just filtered by id but we want to make sure they overlap
            return CourseRun.objects.filter(id=self.object_id)
        elif self.content_type.model == "program":
            return CourseRun.objects.filter(course__program__id=self.object_id)
        else:
            raise ValueError(f"Unexpected content type for {self.content_type.model}")

    @property
    def type_string(self):
        """
        Helper property to return a string representation of the product type,
        e.g.: "courserun", "program"

        Returns:
            str: String representing the product type
        """
        return self.content_type.model

    @property
    def title(self):
        """
        Helper property to return a string representation of the product title,
        e.g.: "courserun.title", "program.title"

        Returns:
            str: String representing the product title
        """
        from courses.models import Program, CourseRun

        content_object = self.content_object
        if isinstance(content_object, Program):
            return content_object.title
        elif isinstance(content_object, CourseRun):
            return content_object.course.title
        else:
            raise ValueError(f"Unexpected content type for {self.content_type.model}")

    @property
    def thumbnail_url(self):
        """
        Helper property to return a thumbnail url of the product.

        Returns:
            thumbnail_url: image url of the product
        """
        from courses.models import Program, CourseRun

        content_object = self.content_object
        if isinstance(content_object, Program):
            catalog_image_url = content_object.catalog_image_url
        elif isinstance(content_object, CourseRun):
            catalog_image_url = content_object.course.catalog_image_url
        else:
            raise ValueError(f"Unexpected product {content_object}")
        return catalog_image_url or static(DEFAULT_COURSE_IMG_PATH)

    @property
    def start_date(self):
        """
        Helper property to return a start date of the product.

        Returns:
            start_date: start date of the product
        """
        from courses.models import Program, CourseRun

        content_object = self.content_object
        if isinstance(content_object, Program):
            return content_object.next_run_date
        elif isinstance(content_object, CourseRun):
            return content_object.course.next_run_date
        else:
            raise ValueError(f"Unexpected product {content_object}")

    def __str__(self):
        """Description of a product"""
        return f"Product for {self.content_object}"


class ProductVersion(TimestampedModel):
    """
    An append-only table for Product, storing information that might be
    updated in the future like price or description.
    """

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="productversions"
    )
    price = models.DecimalField(decimal_places=2, max_digits=20)
    description = models.TextField()
    text_id = models.TextField(null=True)

    class Meta:
        indexes = [models.Index(fields=["created_on"])]

    def save(self, *args, **kwargs):  # pylint: disable=signature-differs
        try:
            self.text_id = getattr(self.product.content_object, "text_id")
        except AttributeError:
            log.error(
                "The content object for this ProductVersion (%s) does not have a `text_id` property",
                str(self.id),
            )
        super().save(*args, **kwargs)

    def __str__(self):
        """Description of a ProductVersion"""
        return f"ProductVersion for {self.description}, ${self.price}"


class Basket(TimestampedModel):
    """
    Represents a User's basket. A Basket is made up of BasketItems. Each Basket is assigned to one user and
    it is reused for each checkout.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        """Description of Basket"""
        return f"Basket for {self.user}"


class BasketItem(TimestampedModel):
    """
    Represents one or more products in a user's basket.
    """

    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    basket = models.ForeignKey(
        Basket, on_delete=models.PROTECT, related_name="basketitems"
    )
    quantity = models.PositiveIntegerField()
    program_run = models.ForeignKey(
        "courses.ProgramRun", on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        """Description of BasketItem"""
        return f"BasketItem of product {self.product} (qty: {self.quantity})"


class OrderManager(models.Manager):
    """
    Add a function to filter on reference id
    """

    def get_by_reference_number(self, reference_number):
        """
        Look up the order id for the reference number and get the order matching it.

        Args:
            reference_number (str): A reference number, a string passed with the Cybersource payload
        Returns:
            Order or B2BOrder: An order
        """
        order_id = get_order_id_by_reference_number(
            reference_number=reference_number,
            prefix=self.model.get_reference_number_prefix(),
        )

        return self.get(id=order_id)


class OrderAbstract(TimestampedModel):
    """An abstract model representing an order"""

    FULFILLED = "fulfilled"
    FAILED = "failed"
    CREATED = "created"
    REFUNDED = "refunded"

    STATUSES = [CREATED, FULFILLED, FAILED, REFUNDED]

    status = models.CharField(
        choices=[(status, status) for status in STATUSES],
        default=CREATED,
        max_length=30,
        db_index=True,
    )

    @property
    def reference_number(self):
        """Create a string with the order id and a unique prefix so we can lookup the order during order fulfillment"""
        return f"{self.get_reference_number_prefix()}-{self.id}"

    class Meta:
        abstract = True


class Order(OrderAbstract, AuditableModel):
    """
    An order containing information for a purchase. Orders which are fulfilled represent successful
    completion of a purchase and are the source of truth for this information.
    """

    purchaser = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    total_price_paid = models.DecimalField(decimal_places=2, max_digits=20)

    objects = OrderManager()

    @staticmethod
    def get_reference_number_prefix():
        """The reference number prefix used to match a CyberSource order fulfillment HTTP request with an order"""
        return f"{REFERENCE_NUMBER_PREFIX}{settings.ENVIRONMENT}"

    def __str__(self):
        """Description for Order"""
        return f"Order #{self.id}, status={self.status}"

    @classmethod
    def get_audit_class(cls):
        return OrderAudit

    def to_dict(self):
        """
        Get a serialized representation of the Order and any attached Basket and Lines
        """
        from ecommerce.api import get_product_version_price_with_discount

        # should be 0 or 1 coupons, and only one line and product
        coupon_redemption = self.couponredemption_set.first()
        line = self.lines.first()

        return {
            **serialize_model_object(self),
            "purchaser_email": self.purchaser.email,
            "lines": [
                {
                    **serialize_model_object(line),
                    "product_version_info": {
                        **serialize_model_object(line.product_version),
                        "product_info": {
                            **serialize_model_object(line.product_version.product),
                            "content_type_string": str(
                                line.product_version.product.content_type
                            ),
                            "content_object": serialize_model_object(
                                line.product_version.product.content_object
                            ),
                        },
                    },
                }
                for line in self.lines.all()
            ],
            "coupons": [
                {
                    **serialize_model_object(coupon_redemption.coupon_version.coupon),
                    "coupon_version_info": {
                        **serialize_model_object(coupon_redemption.coupon_version),
                        "payment_version_info": serialize_model_object(
                            coupon_redemption.coupon_version.payment_version
                        ),
                    },
                }
                for coupon_redemption in self.couponredemption_set.all()
            ],
            "run_enrollments": [
                enrollment.run.courseware_id
                for enrollment in self.courserunenrollment_set.all()
            ],
            "total_price": str(
                get_product_version_price_with_discount(
                    coupon_version=coupon_redemption.coupon_version
                    if coupon_redemption is not None
                    else None,
                    product_version=line.product_version,
                )
                if line is not None
                else ""
            ),
            "receipts": [
                serialize_model_object(receipt) for receipt in self.receipt_set.all()
            ],
        }


class OrderAudit(AuditModel):
    """
    Audit model for Order. This table is only meant for recordkeeping purposes. The serialized
    orders will also include information from any related tables.
    """

    order = models.ForeignKey(Order, null=True, on_delete=models.PROTECT)

    @classmethod
    def get_related_field_name(cls):
        return "order"


class Line(TimestampedModel):
    """
    A line in an Order. This contains information about a specific item which is purchased.
    """

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="lines")
    product_version = models.ForeignKey(ProductVersion, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        """Description for Line"""
        return f"Line for order #{self.order.id}, {self.product_version} (qty: {self.quantity})"


class LineRunSelection(TimestampedModel):
    """
    A mapping from a selection of a run in a program to the order line. Represents a course run selection in a
    submitted order.
    """

    line = models.ForeignKey(
        Line, on_delete=models.CASCADE, related_name="line_selections"
    )
    run = models.ForeignKey("courses.CourseRun", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("line", "run")

    def __str__(self):
        return f"LineRunSelection for order {self.line.order.id}, line {self.line}, run {self.run.courseware_id}"


class ProgramRunLine(TimestampedModel):
    """
    A mapping from a Line to the ProgramRun associated with that Line
    """

    line = models.OneToOneField(
        Line, on_delete=models.CASCADE, related_name="programrunline"
    )
    program_run = models.ForeignKey("courses.ProgramRun", on_delete=models.CASCADE)

    def __str__(self):
        return f"ProgramRunLine for line: {self.id}, order: {self.line.order.id}, text id: {self.program_run.full_readable_id}"


class CouponPaymentQueryset(models.QuerySet):  # pylint: disable=missing-docstring
    def with_ordered_versions(self):
        """Prefetches related CouponPaymentVersions in reverse creation order"""
        return self.prefetch_related(
            models.Prefetch(
                "versions",
                queryset=CouponPaymentVersion.objects.order_by("-created_on"),
                to_attr=ORDERED_VERSIONS_QSET_ATTR,
            )
        ).order_by("name")


class CouponPaymentManager(models.Manager):  # pylint: disable=missing-docstring
    def get_queryset(self):
        """Sets the custom queryset"""
        return CouponPaymentQueryset(self.model, using=self._db)

    def with_ordered_versions(self):
        """Prefetches related CouponPaymentVersions in reverse creation order"""
        return self.get_queryset().with_ordered_versions()


class CouponPayment(TimestampedModel):
    """
    Information about creation of one or more coupons. Most information will go in CouponPaymentVersion.
    name should be a string which never changes and is unique for the coupon payment.
    """

    name = models.CharField(max_length=256, unique=True)
    objects = CouponPaymentManager()

    @property
    def latest_version(self):
        """
        Gets the most recently created CouponPaymentVersion associated with this CouponPayment

        Returns:
            CouponPaymentVersion: The latest CouponPaymentVersion
        """
        return self.versions.order_by("-created_on").first()

    def __str__(self):
        """Description for CouponPayment"""
        return f"CouponPayment {self.name}"


class CouponPaymentVersion(TimestampedModel):
    """
    An append-only table for CouponPayment information. Payment information and coupon details are stored here
    and the latest version for a particular payment is the source of truth for this information.
    """

    PROMO = "promo"
    SINGLE_USE = "single-use"
    COUPON_TYPES = [PROMO, SINGLE_USE]

    PAYMENT_CC = "credit_card"
    PAYMENT_PO = "purchase_order"
    PAYMENT_MKT = "marketing"
    PAYMENT_SALE = "sales"
    PAYMENT_STAFF = "staff"
    PAYMENT_TYPES = [PAYMENT_CC, PAYMENT_PO, PAYMENT_MKT, PAYMENT_SALE, PAYMENT_STAFF]

    tag = models.CharField(max_length=256, null=True, blank=True)
    payment = models.ForeignKey(
        CouponPayment, on_delete=models.PROTECT, related_name="versions"
    )
    automatic = models.BooleanField(default=False)
    coupon_type = models.CharField(
        choices=[(_type, _type) for _type in COUPON_TYPES], max_length=30
    )
    num_coupon_codes = models.PositiveIntegerField()
    max_redemptions = models.PositiveIntegerField()
    max_redemptions_per_user = models.PositiveIntegerField()
    amount = models.DecimalField(
        decimal_places=5,
        max_digits=20,
        help_text="Percent discount for a coupon. Between 0 and 1.",
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, the coupons will not be redeemable before this time",
    )
    expiration_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, the coupons will not be redeemable after this time",
    )
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, null=True, blank=True
    )
    payment_type = models.CharField(
        max_length=128,
        choices=[(paytype, paytype) for paytype in PAYMENT_TYPES],
        null=True,
        blank=True,
    )
    payment_transaction = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["created_on"])]

    def __str__(self):
        """Description for CouponPaymentVersion"""
        return f"CouponPaymentVersion for {self.num_coupon_codes} of type {self.coupon_type}"


class Coupon(TimestampedModel):
    """
    Represents a coupon with a code. The latest CouponVersion for this instance is the source of truth for
    coupon information. Since the coupon_code is the identifier for the coupon, this should never be changed.
    """

    coupon_code = models.CharField(max_length=50)
    payment = models.ForeignKey(CouponPayment, on_delete=models.PROTECT)
    is_global = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    include_future_runs = models.BooleanField(default=False)

    def __str__(self):
        """Description for Coupon"""
        return f"Coupon {self.coupon_code} for {self.payment}"


class CouponVersion(TimestampedModel):
    """
    An append-only table for coupon codes. This should contain any mutable information specific to a coupon
    (at the moment this is only a link to a corresponding CouponPaymentVersion).
    """

    coupon = models.ForeignKey(
        Coupon, on_delete=models.PROTECT, related_name="versions"
    )
    payment_version = models.ForeignKey(CouponPaymentVersion, on_delete=models.PROTECT)

    def __str__(self):
        """Description for CouponVersion"""
        return f"CouponVersion {self.coupon.coupon_code} for {self.payment_version}"


class CouponEligibility(TimestampedModel):
    """
    A link from a coupon to product which the coupon would apply to. There may be many coupons
    which could apply to a product, or a coupon can be valid for many different products.
    """

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    program_run = models.ForeignKey(
        "courses.ProgramRun", on_delete=models.PROTECT, null=True, blank=True
    )

    class Meta:
        unique_together = ("coupon", "product")

    def __str__(self):
        """Description of CouponProduct"""
        return f"CouponProduct for product {self.product}, coupon {self.coupon}"


class CouponSelection(TimestampedModel):
    """
    A link from a Coupon to a Basket the coupon is being used with. At the moment there should only be one
    coupon per basket but this is a many to many table for future flexibility.
    """

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT)
    basket = models.ForeignKey(Basket, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("coupon", "basket")

    def __str__(self):
        """Description of CouponSelection"""
        return f"CouponSelection for basket {self.basket}, coupon {self.coupon}"


class CouponRedemption(TimestampedModel):
    """
    A link from a CouponVersion to an Order. This indicates that a coupon has been used (if the order is fulfilled)
    or that it is intended to be used soon.
    """

    coupon_version = models.ForeignKey(CouponVersion, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("coupon_version", "order")

    def __str__(self):
        """Description of CouponRedemption"""
        return f"CouponRedemption for order {self.order}, coupon version {self.coupon_version}"


class Receipt(TimestampedModel):
    """
    The contents of the message from CyberSource about an Order fulfillment or cancellation. The order
    should always exist but it's nullable in case there is a problem matching the CyberSource response to the order.
    """

    order = models.ForeignKey(Order, null=True, on_delete=models.PROTECT)
    data = JSONField()

    def __str__(self):
        """Description of Receipt"""
        if self.order:
            return f"Receipt for order {self.order.id}"
        else:
            return "Receipt with no attached order"


class CourseRunSelection(TimestampedModel):
    """
    Link between Basket and CourseRun.
    """

    basket = models.ForeignKey(Basket, on_delete=models.PROTECT)
    run = models.ForeignKey("courses.CourseRun", on_delete=models.PROTECT)

    class Meta:
        unique_together = ("basket", "run")

    def __str__(self):
        return f"CourseRunSelection for {self.basket} and {self.run}"


class DataConsentAgreement(TimestampedModel):
    """
    Data consent agreement for a company and course(s)
    """

    content = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    is_global = models.BooleanField(
        default=False,
        help_text="When selected it will override the value of the courses field below",
        verbose_name="All Courses",
    )
    courses = models.ManyToManyField("courses.Course", blank=True)

    def __str__(self):
        return f"DataConsentAgreement for {self.company.name}, products {'(All)' if self.is_global else ','.join([str(course.id) for course in self.courses.all()])}"


class DataConsentUser(TimestampedModel):
    """
    User required to sign an agreement, and the signing date if any.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    agreement = models.ForeignKey(DataConsentAgreement, on_delete=models.PROTECT)
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT)
    consent_date = models.DateTimeField(null=True)

    def __str__(self):
        return f"DataConsentUser {self.user} for {self.agreement}, consent date {self.consent_date}"


class BulkCouponAssignment(models.Model):
    """Records the bulk creation of ProductCouponAssignments"""

    assignment_sheet_id = models.CharField(max_length=100, db_index=True, null=True)
    sheet_last_modified_date = models.DateTimeField(null=True, blank=True)
    last_assignment_date = models.DateTimeField(null=True, blank=True)
    assignments_started_date = models.DateTimeField(null=True, blank=True)
    message_delivery_completed_date = models.DateTimeField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True, null=True)  # UTC
    created_on = models.DateTimeField(auto_now_add=True)  # UTC


class ProductCouponAssignment(TimestampedModel):
    """
    Records the assignment of a product coupon to an email address (in other words, the given
    product coupon can only be redeemed by a User with the given email address)
    """

    email = models.EmailField(blank=False, db_index=True)
    original_email = models.EmailField(null=True, blank=True)
    product_coupon = models.ForeignKey(CouponEligibility, on_delete=models.PROTECT)
    redeemed = models.BooleanField(default=False)
    message_status = models.CharField(
        choices=MAILGUN_EVENT_CHOICES, max_length=15, null=True, blank=True
    )
    message_status_date = models.DateTimeField(null=True, blank=True)
    bulk_assignment = models.ForeignKey(
        BulkCouponAssignment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    def __str__(self):
        return f"ProductCouponAssignment for {self.email}, product coupon {self.product_coupon_id} (redeemed: {self.redeemed})"
