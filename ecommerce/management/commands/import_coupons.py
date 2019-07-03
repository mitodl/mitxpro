"""
Management command to import coupons from a CSV file
"""
import csv
from datetime import datetime
import re
from decimal import Decimal

import pytz
from django.core.management import BaseCommand
from django.db import transaction

from ecommerce.models import (
    Product,
    CouponPaymentVersion,
    CouponPayment,
    Coupon,
    CouponVersion,
    CouponEligibility,
    ProductVersion,
)


def get_eligible_products(
    run_filter, product_filter, all_runs="ALL", all_products="ALL XPRO"
):
    """
    Determine the products eligible for this coupon

    Args:
        run_filter (str): Should be a string that effectively filters products by CourseRun.courseware_id
        product_filter (str): Should be a string that effectively filters products by Product.text_id
        all_runs (str): A string indicating that all runs should be included
        all_products (str): A string indicating that all products should be included

    Returns:
        iterable of Products matching the filter(s)
    """
    base_query = Product.objects.all()
    if product_filter != all_products:
        product_filter = ProductVersion.objects.filter(
            text_id__contains=product_filter
        ).values_list("product", flat=True)
        base_query = base_query.filter(id__in=product_filter)
    if run_filter != all_runs:
        run_filter = ProductVersion.objects.filter(
            text_id__contains=run_filter
        ).values_list("product", flat=True)
        base_query = base_query.filter(id__in=run_filter)
    return base_query.iterator()


def get_active_dates(date_range, forever):
    """
    Determine the start and end dates for the coupon

    Args:
        date_range (str): A string representation of a date range
        forever (str): A string indicating that the coupon expiration date should be far in the future.

    Returns:
        tuple of datetimes

    """
    if date_range == forever:
        return (
            datetime.combine(datetime.now(), datetime.min.time(), pytz.UTC),
            datetime(2500, 1, 1, tzinfo=pytz.UTC),
        )
    return (
        datetime.strptime(dt.strip(), "%m/%d/%y").replace(tzinfo=pytz.UTC)
        for dt in date_range.split("-")
    )


class Command(BaseCommand):
    """
    Management command to import coupons from a CSV file
    """

    help = "Import coupons from a specified CSV file"

    def add_arguments(self, parser):
        """
        Definition of arguments this command accepts
        """
        parser.add_argument(
            "--csv", type=str, help="The CSV file to import coupons from"
        )
        parser.add_argument(
            "--field-run",
            type=str,
            dest="field-run",
            default="RUN",
            help="The CSV field for runs",
        )
        parser.add_argument(
            "--field-product",
            type=str,
            dest="field-product",
            default="COURSE/PROGRAM",
            help="The CSV field for courses/programs",
        )
        parser.add_argument(
            "--field-dates",
            type=str,
            dest="field-dates",
            default="ACTIVE DATES",
            help="The CSV field for coupon dates",
        )
        parser.add_argument(
            "--field-tag",
            type=str,
            dest="field-tag",
            default="INTENDED FOR",
            help="The CSV field for tags",
        )
        parser.add_argument(
            "--field-discount",
            type=str,
            dest="field-discount",
            default="DISCOUNT",
            help="The CSV field for discount amount",
        )
        parser.add_argument(
            "--field-code",
            type=str,
            dest="field-code",
            default="CODE",
            help="The CSV field for coupon code",
        )
        parser.add_argument(
            "--alltime",
            type=str,
            dest="alltime",
            default="ALL TIME",
            help="The CSV value that represents all dates",
        )
        parser.add_argument(
            "--allruns",
            type=str,
            dest="allruns",
            default="ALL",
            help="The CSV value that represents all runs",
        )
        parser.add_argument(
            "--allproducts",
            type=str,
            dest="allproducts",
            default="ALL xPRO",
            help="The CSV value that represents all products",
        )

    def handle(self, *args, **options):
        """Run the command"""
        with open(options["csv"]) as csvfile:
            coupon_reader = csv.DictReader(csvfile)
            for row in coupon_reader:
                run_filter = row[options["field-run"]]
                product_filter = row[options["field-product"]]
                code = row[options["field-code"]]
                discount = Decimal(
                    int(re.match(r"\d+", row[options["field-discount"]])[0]) / 100
                ).quantize(Decimal(10) ** -2)
                self.stdout.write(
                    f"Coupon code '{code}', discount {discount} for '{run_filter}' runs & '{product_filter}' products"
                )

                products = get_eligible_products(
                    run_filter,
                    product_filter,
                    all_runs=options["allruns"],
                    all_products=options["allproducts"],
                )
                if not any(products):
                    self.stderr.write(f"No products/runs found for coupon code {code}")
                    continue

                start, end = get_active_dates(
                    row[options["field-dates"]], options["alltime"]
                )
                with transaction.atomic():
                    cp, _ = CouponPayment.objects.get_or_create(name=code)
                    cpv = CouponPaymentVersion.objects.create(
                        payment=cp,
                        coupon_type=CouponPaymentVersion.PROMO,
                        num_coupon_codes=1,
                        max_redemptions=1_000_000,
                        max_redemptions_per_user=1,
                        amount=discount,
                        tag=row[options["field-tag"]],
                        activation_date=start,
                        expiration_date=end,
                        payment_type=CouponPaymentVersion.PAYMENT_MKT,
                    )
                    coupon, _ = Coupon.objects.get_or_create(
                        coupon_code=code, payment=cp
                    )
                    CouponVersion.objects.create(coupon=coupon, payment_version=cpv)
                    for product in products:
                        self.stdout.write(
                            f"Adding product {product.content_object.text_id} to coupon code {code}"
                        )
                        CouponEligibility.objects.get_or_create(
                            coupon=coupon, product=product
                        )
