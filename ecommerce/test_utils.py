"""Functions used in testing ecommerce"""
from contextlib import contextmanager

from django.db import connection
import faker

from ecommerce.api import generate_cybersource_sa_signature
from ecommerce.utils import (
    create_update_rule,
    create_delete_rule,
    rollback_update_rule,
    rollback_delete_rule,
)

FAKE = faker.Factory.create()


def gen_fake_receipt_data(order=None):
    """
    Helper function to generate a fake signed piece of data
    """
    data = {}
    for _ in range(10):
        data[FAKE.text()] = FAKE.text()
    keys = sorted(data.keys())
    data["signed_field_names"] = ",".join(keys)
    data["unsigned_field_names"] = ""
    data["req_reference_number"] = order.reference_number if order else ""
    data["signature"] = generate_cybersource_sa_signature(data)
    return data


@contextmanager
def unprotect_version_tables():
    """Temporarily unprotect database tables for testing purposes"""
    tables = ["productversion", "couponversion", "couponpaymentversion"]
    with connection.cursor() as cursor:
        try:
            for table in tables:
                cursor.execute(rollback_delete_rule(table))
                cursor.execute(rollback_update_rule(table))
            yield
        finally:
            for table in tables:
                cursor.execute(create_delete_rule(table))
                cursor.execute(create_update_rule(table))
