""" ecommerce serializers """
import pytz
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.fields import IntegerField
from rest_framework.validators import UniqueValidator

from courses.models import Course, CourseRun
from courses.serializers import CourseRunSerializer
from ecommerce import models
from ecommerce.api import latest_product_version, latest_coupon_version
from ecommerce.models import CouponPayment, CouponInvoiceVersion, CouponInvoice, Coupon


class DateTimeTzField(serializers.DateTimeField):
    """ Custom timezone-aware DateTime serializer field """

    def to_representation(self, value):
        return super(DateTimeTzField, self).to_representation(
            value.replace(tzinfo=pytz.UTC)
        )


class ProductSerializer(serializers.ModelSerializer):
    """ Product Serializer """

    title = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()

    def get_title(self, instance):
        """ Return the product title """
        return instance.content_type.get_object_for_this_type(
            pk=instance.object_id
        ).title

    def get_product_type(self, instance):
        """ Return the product type """
        return instance.content_type.model

    class Meta:
        fields = "__all__"
        model = models.Product


class ProductVersionSerializer(serializers.ModelSerializer):
    """ ProductVersion serializer for viewing/updating items in basket """

    type = serializers.SerializerMethodField()
    course_runs = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    def get_type(self, instance):
        """ Return the product version type """
        return instance.product.content_type.model

    def get_course_runs(self, instance):
        """ Return the course runs in the product """
        course_runs = []
        if instance.product.content_type.model == "courserun":
            course_runs.append(instance.product.content_object)
        elif instance.product.content_type.model == "course":
            course_runs.append(instance.product.content_object.first_unexpired_run)
        elif instance.product.content_type.model == "program":
            for course in Course.objects.filter(
                program=instance.product.content_object
            ):
                course_runs.append(course.first_unexpired_run)
        return [
            CourseRunSerializer(instance=course_run).data for course_run in course_runs
        ]

    def get_thumbnail_url(self, instance):
        """Return the thumbnail for the course or program"""
        content_object = instance.product.content_object
        if isinstance(content_object, CourseRun):
            thumbnail = content_object.course.thumbnail
        else:
            thumbnail = content_object.thumbnail

        if thumbnail:
            return thumbnail.url
        else:
            return static("images/mit-dome.png")

    class Meta:
        fields = ["id", "price", "description", "type", "course_runs", "thumbnail_url"]
        model = models.ProductVersion


class CouponSelectionSerializer(serializers.ModelSerializer):
    """CouponSelection serializer for viewing/updating coupons in basket"""

    code = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    targets = serializers.SerializerMethodField()

    def get_code(self, instance):
        """ Get the coupon code"""
        return instance.coupon.coupon_code

    def get_amount(self, instance):
        """ Get the coupon discount amount """
        return latest_coupon_version(instance.coupon).invoice_version.amount

    def get_targets(self, instance):
        """ Get the product version id(s) in the basket the coupon applies to"""
        eligible_product_ids = (
            models.CouponEligibility.objects.select_related("coupon", "product")
            .filter(
                coupon__coupon_code=instance.coupon.coupon_code,
                coupon__enabled=True,
                product__in=instance.basket.basketitems.values_list(
                    "product", flat=True
                ),
            )
            .values_list("product", flat=True)
        )
        return [
            latest_product_version(product).id
            for product in models.Product.objects.filter(id__in=eligible_product_ids)
        ]

    class Meta:
        fields = ["code", "amount", "targets"]
        model = models.CouponSelection


class BasketSerializer(serializers.ModelSerializer):
    """Basket model serializer"""

    items = serializers.SerializerMethodField()
    coupons = serializers.SerializerMethodField()

    def get_items(self, instance):
        """ Get the basket items """
        return [
            ProductVersionSerializer(instance=latest_product_version(item.product)).data
            for item in instance.basketitems.all()
        ]

    def get_coupons(self, instance):
        """ Get the basket coupons """
        return [
            CouponSelectionSerializer(instance=coupon_selection).data
            for coupon_selection in models.CouponSelection.objects.filter(
                basket=instance
            )
        ]

    class Meta:
        fields = ["items", "coupons"]
        model = models.Basket


class CouponInvoiceSerializer(serializers.ModelSerializer):
    """ Serializer for coupon invoices """

    class Meta:
        fields = "__all__"
        model = models.CouponInvoice


class CouponInvoiceVersionSerializer(serializers.ModelSerializer):
    """ Serializer for coupon invoice versions """

    invoice = CouponInvoiceSerializer()

    class Meta:
        fields = "__all__"
        model = models.CouponInvoiceVersion


class BaseCouponSerializer(serializers.Serializer):
    """ Base serializer for coupon creation data """

    tag = serializers.CharField(
        validators=[UniqueValidator(queryset=CouponInvoice.objects.all())]
    )
    amount = serializers.DecimalField(decimal_places=2, max_digits=20)
    automatic = serializers.BooleanField(default=False)
    activation_date = DateTimeTzField()
    expiration_date = DateTimeTzField()
    products = serializers.ListField(child=IntegerField())
    max_redemptions = serializers.IntegerField(default=1)
    max_redemptions_per_user = serializers.IntegerField(default=1)
    coupon_type = serializers.ChoiceField(
        choices=[(_type, _type) for _type in CouponInvoiceVersion.COUPON_TYPES]
    )
    num_coupon_codes = serializers.IntegerField(default=1)
    company = serializers.CharField(max_length=512, allow_null=False)
    payment_type = serializers.ChoiceField(
        choices=[(_type, _type) for _type in CouponPayment.PAYMENT_TYPES]
    )


class SingleUseCouponSerializer(BaseCouponSerializer):
    """ Serializer for creating single-use coupons """

    payment_id = serializers.CharField(allow_null=False)


class PromoCouponSerializer(BaseCouponSerializer):
    """ Serializer for creating promo coupons """

    coupon_code = serializers.CharField(
        max_length=50, validators=[UniqueValidator(queryset=Coupon.objects.all())]
    )
    payment_id = serializers.CharField(allow_null=True)


class CouponOrderSerializer(serializers.ModelSerializer):
    """ Serializer for coupon orders """

    invoice_version = CouponInvoiceVersionSerializer()

    class Meta:
        model = models.CouponPayment
        fields = "__all__"
