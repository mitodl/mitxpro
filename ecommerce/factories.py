"""
Factories for ecommerce models
"""
from datetime import timezone

from factory import fuzzy, Faker, LazyAttribute, SubFactory, Trait, post_generation
from factory.django import DjangoModelFactory
import faker

from courses.factories import CourseRunFactory, ProgramRunFactory
from ecommerce import models
from ecommerce.test_utils import gen_fake_receipt_data
from mitxpro.utils import now_in_utc
from users.factories import UserFactory


FAKE = faker.Factory.create()


class CompanyFactory(DjangoModelFactory):
    """Factory for Company"""

    name = fuzzy.FuzzyText()

    class Meta:
        model = models.Company


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
    program_run = None

    class Meta:
        model = models.BasketItem

    class Params:
        with_program_run = Trait(program_run=SubFactory(ProgramRunFactory))


class OrderFactory(DjangoModelFactory):
    """Factory for Order"""

    purchaser = SubFactory(UserFactory)
    status = fuzzy.FuzzyChoice(choices=models.Order.STATUSES)
    total_price_paid = fuzzy.FuzzyDecimal(low=0, high=100)

    class Meta:
        model = models.Order


class LineFactory(DjangoModelFactory):
    """Factory for Line"""

    order = SubFactory(OrderFactory)
    product_version = SubFactory(ProductVersionFactory)
    quantity = fuzzy.FuzzyInteger(1, 5)

    class Meta:
        model = models.Line


class LineRunSelectionFactory(DjangoModelFactory):
    """Factory for LineRunSelection"""

    line = SubFactory(LineFactory)
    run = SubFactory(CourseRunFactory)

    class Meta:
        model = models.LineRunSelection


class CouponPaymentFactory(DjangoModelFactory):
    """Factory for CouponPayment"""

    name = fuzzy.FuzzyText()

    class Meta:
        model = models.CouponPayment


class CouponPaymentVersionFactory(DjangoModelFactory):
    """Factory for CouponPaymentVersion"""

    payment = SubFactory(CouponPaymentFactory)
    tag = fuzzy.FuzzyText()
    coupon_type = fuzzy.FuzzyChoice(models.CouponPaymentVersion.COUPON_TYPES)
    num_coupon_codes = fuzzy.FuzzyInteger(1, 10)
    max_redemptions = fuzzy.FuzzyInteger(1, 10)
    max_redemptions_per_user = fuzzy.FuzzyInteger(1, 3)
    amount = fuzzy.FuzzyDecimal(0, 1, precision=5)
    company = SubFactory(CompanyFactory)
    activation_date = Faker(
        "date_time_this_year", before_now=True, after_now=False, tzinfo=timezone.utc
    )
    expiration_date = Faker(
        "date_time_this_year", before_now=False, after_now=True, tzinfo=timezone.utc
    )

    class Meta:
        model = models.CouponPaymentVersion


class CouponFactory(DjangoModelFactory):
    """Factory for Coupon"""

    coupon_code = fuzzy.FuzzyText()
    payment = SubFactory(CouponPaymentFactory)
    is_global = False

    class Meta:
        model = models.Coupon


class CouponVersionFactory(DjangoModelFactory):
    """Factory for CouponVersion"""

    coupon = SubFactory(CouponFactory)
    payment_version = SubFactory(CouponPaymentVersionFactory)

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


class CourseRunSelectionFactory(DjangoModelFactory):
    """Factory for CourseRunSelection"""

    basket = SubFactory(BasketFactory)
    run = SubFactory(CourseRunFactory)

    class Meta:
        model = models.CourseRunSelection


class DataConsentAgreementFactory(DjangoModelFactory):
    """Factory for DataConsentAgreement"""

    content = fuzzy.FuzzyText()
    company = SubFactory(CompanyFactory)
    is_global = False

    @post_generation
    # pylint: disable=unused-argument
    def courses(self, create, extracted, **kwargs):
        """Create courses for DCA"""
        if not create:
            return

        if extracted:
            for course in extracted:
                self.courses.add(course)

    class Meta:
        model = models.DataConsentAgreement


class DataConsentUserFactory(DjangoModelFactory):
    """Factory for DataConsentUser"""

    user = SubFactory(UserFactory)
    agreement = SubFactory(DataConsentAgreementFactory)
    coupon = SubFactory(CouponFactory)
    consent_date = fuzzy.FuzzyDateTime(start_dt=now_in_utc())

    class Meta:
        model = models.DataConsentUser


class BulkCouponAssignmentFactory(DjangoModelFactory):
    """Factory for BulkCouponAssignment"""

    assignment_sheet_id = Faker("pystr", max_chars=43)

    class Meta:
        model = models.BulkCouponAssignment


class ProductCouponAssignmentFactory(DjangoModelFactory):
    """Factory for ProductCouponAssignment"""

    email = fuzzy.FuzzyText(suffix="@example.com")
    product_coupon = SubFactory(CouponEligibilityFactory)
    bulk_assignment = SubFactory(BulkCouponAssignmentFactory)

    class Meta:
        model = models.ProductCouponAssignment
