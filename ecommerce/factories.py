"""
Factories for ecommerce models
"""
from datetime import timezone

from factory import fuzzy, Faker, LazyAttribute, SubFactory
from factory.django import DjangoModelFactory
import faker

from courses.factories import CourseRunFactory
from ecommerce import models
from ecommerce.test_utils import gen_fake_receipt_data
from users.factories import UserFactory


FAKE = faker.Factory.create()


class ProductFactory(DjangoModelFactory):
    """Factory for Product"""

    content_object = SubFactory(CourseRunFactory)

    class Meta:
        model = models.Product


class ProductVersionFactory(DjangoModelFactory):
    """Factory for ProductVersion"""

    product = SubFactory(ProductFactory)
    price = fuzzy.FuzzyDecimal(low=1, high=123)
    description = fuzzy.FuzzyText()

    class Meta:
        model = models.ProductVersion


class BasketFactory(DjangoModelFactory):
    """Factory for Basket"""

    user = SubFactory(UserFactory)

    class Meta:
        model = models.Basket


class BasketItemFactory(DjangoModelFactory):
    """Factory for BasketItem"""

    product = SubFactory(ProductFactory)
    basket = SubFactory(BasketFactory)
    quantity = fuzzy.FuzzyInteger(1, 5)

    class Meta:
        model = models.BasketItem


class OrderFactory(DjangoModelFactory):
    """Factory for Order"""

    purchaser = SubFactory(UserFactory)
    status = fuzzy.FuzzyChoice(choices=models.Order.STATUSES)

    class Meta:
        model = models.Order


class LineFactory(DjangoModelFactory):
    """Factory for Line"""

    order = SubFactory(OrderFactory)
    product_version = SubFactory(ProductVersionFactory)
    quantity = fuzzy.FuzzyInteger(1, 5)

    class Meta:
        model = models.Line


class CouponInvoiceFactory(DjangoModelFactory):
    """Factory for CouponInvoice"""

    tag = fuzzy.FuzzyText()

    class Meta:
        model = models.CouponInvoice


class CouponInvoiceVersionFactory(DjangoModelFactory):
    """Factory for CouponInvoiceVersion"""

    invoice = SubFactory(CouponInvoiceFactory)

    coupon_type = fuzzy.FuzzyChoice(models.CouponInvoiceVersion.COUPON_TYPES)
    num_coupon_codes = fuzzy.FuzzyInteger(1, 10)
    max_redemptions = fuzzy.FuzzyInteger(1, 10)
    max_redemptions_per_user = fuzzy.FuzzyInteger(1, 3)
    amount = fuzzy.FuzzyDecimal(0, 1)
    activation_date = Faker(
        "date_time_this_year", before_now=True, after_now=False, tzinfo=timezone.utc
    )
    expiration_date = Faker(
        "date_time_this_year", before_now=False, after_now=True, tzinfo=timezone.utc
    )

    class Meta:
        model = models.CouponInvoiceVersion


class CouponFactory(DjangoModelFactory):
    """Factory for Coupon"""

    coupon_code = fuzzy.FuzzyText()
    invoice = SubFactory(CouponInvoiceFactory)

    class Meta:
        model = models.Coupon


class CouponVersionFactory(DjangoModelFactory):
    """Factory for CouponVersion"""

    coupon = SubFactory(CouponFactory)
    invoice_version = SubFactory(CouponInvoiceVersionFactory)

    class Meta:
        model = models.CouponVersion


class CouponEligibilityFactory(DjangoModelFactory):
    """Factory for CouponEligibility"""

    coupon = SubFactory(CouponFactory)
    product = SubFactory(ProductFactory)

    class Meta:
        model = models.CouponEligibility


class CouponSelectionFactory(DjangoModelFactory):
    """Factory for CouponSelection"""

    coupon = SubFactory(CouponFactory)
    basket = SubFactory(BasketFactory)

    class Meta:
        model = models.CouponSelection


class CouponRedemptionFactory(DjangoModelFactory):
    """Factory for CouponRedemption"""

    coupon_version = SubFactory(CouponVersionFactory)
    order = SubFactory(OrderFactory)

    class Meta:
        model = models.CouponRedemption


class ReceiptFactory(DjangoModelFactory):
    """Factory for Receipt"""

    order = SubFactory(OrderFactory)
    data = LazyAttribute(lambda receipt: gen_fake_receipt_data(receipt.order))

    class Meta:
        model = models.Receipt
