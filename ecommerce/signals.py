"""Signals for ecommerce models"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from ecommerce.models import ProductVersion, Product, CouponEligibility
from hubspot.task_helpers import sync_hubspot_product

from courses.models import CourseRun


@receiver(post_save, sender=ProductVersion, dispatch_uid="product_version_post_save")
def sync_product(sender, instance, created, **kwargs):  # pylint:disable=unused-argument
    """
    Sync product to hubspot
    """
    sync_hubspot_product(instance.product)


@receiver(post_save, sender=Product, dispatch_uid="product_post_save")
def apply_coupon_on_all_runs(
    sender, instance, created, **kwargs
):  # pylint:disable=unused-argument
    """
    Apply coupons to all courseruns of a course, if `include_future_runs = True`
    """
    if not created:
        return

    content_object = instance.content_object
    products = None

    # we are not using program runs, so we can skip them now
    if not isinstance(content_object, CourseRun):
        return

    runs = CourseRun.objects.get(id=instance.object_id).course.courseruns.all()
    products = Product.objects.filter(object_id__in=runs).exclude(id=instance.id)

    if not products:
        return

    eligible_coupons = (
        CouponEligibility.objects.filter(
            product__in=products, coupon__include_future_runs=True
        )
        .select_related("coupon")
        .values_list("coupon", flat=True)
        .distinct()
    )

    for coupon_id in eligible_coupons:
        CouponEligibility.objects.update_or_create(
            product=instance, coupon_id=coupon_id
        )
