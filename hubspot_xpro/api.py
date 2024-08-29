"""Generate Hubspot message bodies for various model objects"""

import logging
import re
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from hubspot.crm.objects import SimplePublicObject, SimplePublicObjectInput
from mitol.hubspot_api.api import (
    HubspotApi,
    HubspotAssociationType,
    HubspotObjectType,
    associate_objects_request,
    find_contact,
    find_deal,
    find_line_item,
    find_product,
    get_all_objects,
    get_line_items_for_deal,
    make_object_properties_message,
    transform_object_properties,
    upsert_object_request,
)
from mitol.hubspot_api.models import HubspotObject

from b2b_ecommerce.constants import B2B_ORDER_PREFIX
from b2b_ecommerce.models import B2BLine, B2BOrder
from ecommerce.models import Line, Order, Product, ProductVersion
from users.models import User

log = logging.getLogger(__name__)


def make_contact_sync_message(user_id: int) -> SimplePublicObjectInput:
    """
    Create the body of a sync message for a contact. This will flatten the contained LegalAddress and Profile
    serialized data into one larger serializable dict

    Args:
        user_id (int): User id

    Returns:
        SimplePublicObjectInput: input object for upserting User data to Hubspot
    """
    from users.serializers import UserSerializer

    contact_properties_map = {
        "email": "email",
        "name": "name",
        "first_name": "firstname",
        "last_name": "lastname",
        "street_address": "address",
        "city": "city",
        "country": "country",
        "state_or_territory": "state",
        "postal_code": "zip",
        "birth_year": "birth_year",
        "gender": "gender",
        "company": "company",
        "company_size": "company_size",
        "industry": "industry",
        "job_title": "jobtitle",
        "job_function": "job_function",
        "leadership_level": "leadership_level",
        "highest_education": "highest_education",
        "vat_id": "vat_id",
    }

    user = User.objects.get(id=user_id)
    properties = UserSerializer(user).data
    properties.update(properties.pop("legal_address") or {})
    properties.update(properties.pop("profile") or {})
    if "street_address" in properties:
        properties["street_address"] = "\n".join(properties.pop("street_address"))
    hubspot_props = transform_object_properties(properties, contact_properties_map)
    return make_object_properties_message(hubspot_props)


def make_b2b_contact_sync_message(email: str) -> SimplePublicObjectInput:
    """
    Create a hubspot sync input object for a User.

    Args:
        email (string): User email

    Returns:
        SimplePublicObjectInput: input object for upserting B2B contact data to Hubspot
    """
    return make_object_properties_message({"email": email})


def make_b2b_deal_sync_message(order_id):
    """
    Create a hubspot sync input object for a B2BOrder.

    Args:
        order_id (int): B2BOrder id

    Returns:
        SimplePublicObjectInput: input object for upserting B2BOrder data to Hubspot
    """
    from hubspot_xpro.serializers import B2BOrderToDealSerializer

    order = B2BOrder.objects.get(id=order_id)
    properties = B2BOrderToDealSerializer(order).data
    return make_object_properties_message(properties)


def make_deal_sync_message(order_id: int) -> SimplePublicObjectInput:
    """
    Create a hubspot sync input object for an Order.

    Args:
        order_id (int): Order id

    Returns:
        SimplePublicObjectInput: input object for upserting Order data to Hubspot
    """
    from hubspot_xpro.serializers import OrderToDealSerializer

    order = Order.objects.get(id=order_id)
    properties = OrderToDealSerializer(order).data
    return make_object_properties_message(properties)


def make_line_item_sync_message(line_id: int) -> SimplePublicObjectInput:
    """
    Create a hubspot sync input object for a Line.

    Args:
        line_id (int): Line id

    Returns:
        SimplePublicObjectInput: input object for upserting Line data to Hubspot
    """
    from hubspot_xpro.serializers import LineSerializer

    line = Line.objects.get(id=line_id)
    properties = LineSerializer(line).data
    return make_object_properties_message(properties)


def make_b2b_line_sync_message(order_id: int) -> SimplePublicObjectInput:
    """
    Create a hubspot sync input object for a B2BLine.

    Args:
        order_id (int): B2BOrder id

    Returns:
        SimplePublicObjectInput: input object for upserting B2BLine data to Hubspot
    """
    from hubspot_xpro.serializers import B2BOrderToLineItemSerializer

    order = B2BOrder.objects.get(id=order_id)
    properties = B2BOrderToLineItemSerializer(order).data
    return make_object_properties_message(properties)


def make_product_sync_message(product_id: int) -> SimplePublicObjectInput:
    """
    Create a hubspot sync input object for a product.

    Args:
        product_id (int): Product id

    Returns:
        SimplePublicObjectInput: input object for upserting Product data to Hubspot
    """
    from hubspot_xpro.serializers import ProductSerializer

    product = Product.objects.get(id=product_id)
    properties = ProductSerializer(product).data
    return make_object_properties_message(properties)


def format_product_name(product: Product) -> str:
    """
    Get the product name as it should appear in Hubspot

    Args:
        product(Product): The product to return a name for

    Returns:
        str: The name of the Product as it should appear in Hubspot
    """
    product_obj = product.content_type.get_object_for_this_type(pk=product.object_id)
    title_run_id = re.findall(r"\+R(\d+)$", product_obj.text_id)
    title_suffix = f"Run {title_run_id[0]}" if title_run_id else product_obj.text_id
    return f"{product_obj.title}: {title_suffix}"


def sync_contact_hubspot_ids_to_db():
    """
    Create HubspotObjects for all contacts in Hubspot

    Returns:
        bool: True if hubspot id matches found for all Users
    """
    contacts = get_all_objects(
        HubspotObjectType.CONTACTS.value, properties=["email", "hs_additional_emails"]
    )
    content_type = ContentType.objects.get_for_model(User)
    for contact in contacts:
        user = User.objects.filter(email__iexact=contact.properties["email"]).first()
        if not user and contact.properties["hs_additional_emails"]:
            alt_email_q = Q()
            for alt_email in contact.properties["hs_additional_emails"].split(";"):
                alt_email_q |= Q(email__iexact=alt_email)
            user = User.objects.filter(alt_email_q).first()
        if user:
            HubspotObject.objects.update_or_create(
                content_type=content_type,
                object_id=user.id,
                defaults={"hubspot_id": contact.id},
            )
    return (
        User.objects.count()
        == HubspotObject.objects.filter(content_type=content_type).count()
    )


def sync_product_hubspot_ids_to_db() -> bool:
    """
    Create HubspotObjects for products, return True if all products have hubspot ids

    Returns:
        bool: True if hubspot id matches found for all Products
    """
    content_type = ContentType.objects.get_for_model(Product)
    product_mapping = {}
    for product in Product.objects.all():
        product_mapping.setdefault(format_product_name(product), []).append(product.id)
    products = get_all_objects(HubspotObjectType.PRODUCTS.value)
    for product in products:
        matching_products = product_mapping.get(product.properties["name"])
        if not matching_products:
            continue
        if len(matching_products) > 1:
            # Narrow down by price
            matched_subquery = HubspotObject.objects.filter(
                content_type=content_type
            ).values_list("object_id", flat=True)
            matching_product = (
                ProductVersion.objects.exclude(product_id__in=matched_subquery)
                .filter(
                    product_id__in=matching_products,
                    price=Decimal(product.properties["price"]),
                )
                .order_by("-created_on")
                .values_list("product", flat=True)
                .first()
            )
        else:
            matching_product = matching_products[0]
        if matching_product:
            HubspotObject.objects.update_or_create(
                content_type=content_type,
                object_id=matching_product,
                defaults={"hubspot_id": product.id},
            )
    return (
        Product.objects.count()
        == HubspotObject.objects.filter(content_type=content_type).count()
    )


def sync_deal_hubspot_ids_to_db() -> bool:
    """
    Create Hubspot objects for orders and lines, return True if all orders
    (and optionally lines) have hubspot ids

    Returns:
        bool: True if matches found for all Orders and B2BOrders (and optionally their lines)
    """
    ct_order = ContentType.objects.get_for_model(Order)
    ct_b2b_order = ContentType.objects.get_for_model(B2BOrder)
    deals = get_all_objects(
        HubspotObjectType.DEALS.value, properties=["dealname", "amount"]
    )
    lines_synced = True
    for deal in deals:
        deal_name = deal.properties["dealname"]
        deal_price = Decimal(deal.properties["amount"] or "0.00")
        try:
            object_id = int(deal_name.split("-")[-1])
        except ValueError:
            # this isn't a deal that can be synced, ie "AMx Run 3 - SPIN MASTER"
            continue
        if deal_name.startswith(B2B_ORDER_PREFIX):
            order = B2BOrder.objects.filter(
                id=object_id, total_price=deal_price
            ).first()
            content_type = ct_b2b_order
        else:
            order = Order.objects.filter(
                id=object_id, total_price_paid=deal_price
            ).first()
            content_type = ct_order
        if order:
            HubspotObject.objects.update_or_create(
                content_type=content_type,
                object_id=order.id,
                defaults={"hubspot_id": deal.id},
            )
            if not sync_deal_line_hubspot_ids_to_db(order, deal.id):
                lines_synced = False
    return (
        Order.objects.count() + B2BOrder.objects.count()
    ) == HubspotObject.objects.filter(
        content_type__in=(ct_order, ct_b2b_order)
    ).count() and lines_synced


def sync_deal_line_hubspot_ids_to_db(order, hubspot_order_id) -> bool:
    """
    Create HubspotObjects for all of a deal's line items, return True if matches found for all lines

    Args:
        order(Order or B2BOrder): The order to sync Hubspot line items for
        hubspot_order_id(str): The Hubspot deal id

    Returns:
        bool: True if matches found for all the order lines

    """
    client = HubspotApi()
    line_items = get_line_items_for_deal(hubspot_order_id)
    is_b2b = isinstance(order, B2BOrder)
    order_line = order.line if is_b2b else order.lines.first()

    matches = 0
    expected_matches = 1 if is_b2b else order.lines.count()
    if is_b2b or len(line_items) == 1:
        HubspotObject.objects.update_or_create(
            content_type=ContentType.objects.get_for_model(order_line),
            object_id=order_line.id,
            defaults={"hubspot_id": line_items[0].id},
        )
        matches += 1
    elif not is_b2b:  # Multiple lines, need to match by product and quantity
        for line in line_items:
            details = client.crm.line_items.basic_api.get_by_id(line.id)
            hs_product = HubspotObject.objects.filter(
                hubspot_id=details.properties["hs_product_id"],
                content_type=ContentType.objects.get_for_model(Product),
            ).first()
            if hs_product:
                product_id = hs_product.object_id
                matching_line = Line.objects.filter(
                    order=order,
                    product_version__product__id=product_id,
                    quantity=int(line.properties["quantity"]),
                ).first()
                if matching_line:
                    HubspotObject.objects.update_or_create(
                        content_type=ContentType.objects.get_for_model(Line),
                        object_id=matching_line.id,
                        defaults={"hubspot_id": line.id},
                    )
                    matches += 1
    return matches == expected_matches


def get_hubspot_id_for_object(
    obj: Order or B2BOrder or Product or Line or B2BLine or User,
    raise_error: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    Get the hubspot id for an object, querying Hubspot if necessary

    Args:
        obj(object): The object (Order, B2BOrder, Product, Line, B2BLine or User) to get the id for
        raise_error(bool): raise an error if not found (default False)

    Returns:
        The hubspot id for the object if it has been previously synced to Hubspot.
        Raises a ValueError if no matching Hubspot object can be found.
    """
    from hubspot_xpro.serializers import get_hubspot_serializer

    content_type = ContentType.objects.get_for_model(obj)
    hubspot_obj = HubspotObject.objects.filter(
        object_id=obj.id, content_type=content_type
    ).first()
    if hubspot_obj:
        return hubspot_obj.hubspot_id
    if isinstance(obj, User):
        hubspot_obj = find_contact(obj.email)
    elif isinstance(obj, (B2BOrder, Order)):  # noqa: UP038
        serialized_deal = get_hubspot_serializer(obj).data
        hubspot_obj = find_deal(
            name=serialized_deal["dealname"],
            amount=serialized_deal["amount"],
            raise_count_error=raise_error,
        )
    elif isinstance(obj, (Line, B2BLine)):  # noqa: UP038
        serialized_line = get_hubspot_serializer(obj).data
        order_id = get_hubspot_id_for_object(obj.order)
        if order_id:
            hubspot_obj = find_line_item(
                order_id,
                quantity=serialized_line["quantity"],
                hs_product_id=serialized_line["hs_product_id"],
                raise_count_error=raise_error,
            )
    elif isinstance(obj, Product):
        serialized_product = get_hubspot_serializer(obj).data
        hubspot_obj = find_product(
            serialized_product["name"],
            price=serialized_product["price"],
            raise_count_error=raise_error,
        )
    if hubspot_obj and hubspot_obj.id:  # noqa: RET503
        HubspotObject.objects.update_or_create(
            object_id=obj.id,
            content_type=content_type,
            defaults={"hubspot_id": hubspot_obj.id},
        )
        return hubspot_obj.id
    elif raise_error:
        raise ValueError(
            "Hubspot id could not be found for %s for id %d"
            % (content_type.name, obj.id)
        )


def sync_b2b_contact_with_hubspot(order_id: int) -> SimplePublicObject:
    """
    Sync a B2B order email with a hubspot contact

    Args:
        order_id(int): The B2BOrder id

    Returns:
        SimplePublicObject: The hubspot contact object
    """
    b2b_order = B2BOrder.objects.get(id=order_id)
    body = make_b2b_contact_sync_message(b2b_order.email)
    content_type = ContentType.objects.get_for_model(User)

    result = upsert_object_request(
        content_type, HubspotObjectType.CONTACTS.value, body=body, ignore_conflict=True
    )
    # Create association between deal and contact
    associate_objects_request(
        HubspotObjectType.DEALS.value,
        get_hubspot_id_for_object(b2b_order),
        HubspotObjectType.CONTACTS.value,
        result.id,
        HubspotAssociationType.DEAL_CONTACT.value,
    )
    return result


def sync_b2b_line_with_hubspot(b2b_order_id: int) -> SimplePublicObject:
    """
    Sync a B2BLine with a hubspot line item

    Args:
        b2b_order_id(int): The B2BOrder id

    Returns:
        SimplePublicObject: The hubspot line_item object
    """
    b2b_line = B2BLine.objects.get(order__id=b2b_order_id)
    body = make_b2b_line_sync_message(b2b_order_id)
    content_type = ContentType.objects.get_for_model(B2BLine)

    # Check if a matching hubspot object has been or can be synced
    get_hubspot_id_for_object(b2b_line)

    result = upsert_object_request(
        content_type, HubspotObjectType.LINES.value, object_id=b2b_line.id, body=body
    )

    # Associate the parent deal with the line item
    associate_objects_request(
        HubspotObjectType.LINES.value,
        result.id,
        HubspotObjectType.DEALS.value,
        get_hubspot_id_for_object(B2BOrder.objects.get(id=b2b_order_id)),
        HubspotAssociationType.LINE_DEAL.value,
    )
    return result


def sync_b2b_deal_with_hubspot(order_id: int) -> SimplePublicObject:
    """
    Sync a B2BOrder with a hubspot_xpro deal

    Args:
        order_id(int): The B2BOrder id

    Returns:
        SimplePublicObject: The hubspot deal object
    """
    # Sync the B2B order
    body = make_b2b_deal_sync_message(order_id)
    content_type = ContentType.objects.get_for_model(B2BOrder)

    # Check if a matching hubspot object has been or can be synced
    get_hubspot_id_for_object(B2BOrder.objects.get(id=order_id))

    result = upsert_object_request(
        content_type, HubspotObjectType.DEALS.value, object_id=order_id, body=body
    )

    # Now sync the contact and line
    sync_b2b_line_with_hubspot(order_id)
    sync_b2b_contact_with_hubspot(order_id)

    return result


def sync_line_item_with_hubspot(line_id: int) -> SimplePublicObject:
    """
    Sync a Line with a hubspot line item

    Args:
        line_id(int): The Line id

    Returns:
        SimplePublicObject: The hubspot line_item object
    """
    line = Line.objects.get(id=line_id)
    body = make_line_item_sync_message(line_id)
    content_type = ContentType.objects.get_for_model(Line)

    # Check if a matching hubspot object has been or can be synced
    get_hubspot_id_for_object(line)

    # Create or update the line items
    result = upsert_object_request(
        content_type, HubspotObjectType.LINES.value, object_id=line_id, body=body
    )
    # Associate the parent deal with the line item
    associate_objects_request(
        HubspotObjectType.LINES.value,
        result.id,
        HubspotObjectType.DEALS.value,
        get_hubspot_id_for_object(line.order),
        HubspotAssociationType.LINE_DEAL.value,
    )
    return result


def sync_deal_with_hubspot(order_id: int) -> SimplePublicObject:
    """
    Sync an Order with a hubspot deal

    Args:
        order_id(int): The Order id

    Returns:
        SimplePublicObject: The hubspot deal object
    """
    order = Order.objects.get(id=order_id)
    body = make_deal_sync_message(order_id)
    content_type = ContentType.objects.get_for_model(Order)

    # Check if a matching hubspot object has been or can be synced
    get_hubspot_id_for_object(order)

    # Create or update the order aka deal
    result = upsert_object_request(
        content_type, HubspotObjectType.DEALS.value, object_id=order_id, body=body
    )
    # Create association between deal and contact
    associate_objects_request(
        HubspotObjectType.DEALS.value,
        result.id,
        HubspotObjectType.CONTACTS.value,
        get_hubspot_id_for_object(order.purchaser),
        HubspotAssociationType.DEAL_CONTACT.value,
    )

    for line in order.lines.all():
        sync_line_item_with_hubspot(line.id)
    return result


def sync_product_with_hubspot(product_id: int) -> SimplePublicObject:
    """
    Sync a Product with a hubspot product

    Args:
        product_id(int): The Product id

    Returns:
        SimplePublicObject: The hubspot product object
    """
    body = make_product_sync_message(product_id)
    content_type = ContentType.objects.get_for_model(Product)

    # Check if a matching hubspot object has been or can be synced
    get_hubspot_id_for_object(Product.objects.get(id=product_id))

    return upsert_object_request(
        content_type, HubspotObjectType.PRODUCTS.value, object_id=product_id, body=body
    )


def sync_contact_with_hubspot(user_id: int) -> SimplePublicObject:
    """
    Sync a user with a hubspot_xpro contact

    Args:
        user_id(int): The User id

    Returns:
        SimplePublicObject: The hubspot contact object
    """
    body = make_contact_sync_message(user_id)
    content_type = ContentType.objects.get_for_model(User)

    return upsert_object_request(
        content_type, HubspotObjectType.CONTACTS.value, object_id=user_id, body=body
    )


MODEL_FUNCTION_MAPPING = {
    "user": make_contact_sync_message,
    "order": make_deal_sync_message,
    "b2border": make_b2b_deal_sync_message,
    "line": make_line_item_sync_message,
    "b2bline": make_b2b_line_sync_message,
    "product": make_product_sync_message,
}
