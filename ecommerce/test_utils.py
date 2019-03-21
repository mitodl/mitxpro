"""Functions used in testing ecommerce"""
import faker

from ecommerce.api import generate_cybersource_sa_signature, make_reference_id


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
    data["req_reference_number"] = make_reference_id(order) if order else ""
    data["signature"] = generate_cybersource_sa_signature(data)
    return data
