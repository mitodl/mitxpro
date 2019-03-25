## Title for RFC
ecommerce REST APIs in mitxpro

### Abstract

The REST APIs for ecommerce provide ways for end users to update their basket and execute purchases.
CyberSource also uses a REST API to communicate to our server the status of a payment.

One principle guiding these REST APIs is that our web server should never handle credit card numbers
or other similarly sensitive information. Instead this information will be communicated
directly to CyberSource from the frontend, or left out entirely so that the user enters
this information on CyberSource's form.

### /api/products/

This API provides a view into what products are available for a user to purchase. This API
will be used by product listing pages but won't be needed on the checkout page. The same
information will be available via the basket REST API.

#### GET

A response would look like

    [
        {
            "id": 3,  // this is ProductVersion.id, not Product.id
            "description": "Supply Chain Management",
            "price": "67.89",
            "type": "program",
            "course_runs": [
                {
                    "title": "Supply Chain Analytics",
                    "courseware_id": "course_id",
                    "courseware_url": "course_url",
                    "start_date": "iso8601 date here",
                    "end_date": "iso8601 date here",
                }
            ]
        },
        ...
    ]

The `course_runs` field is used to provide the UI with more information to show
to the user about what they're buying. A product which is a program bundle would
have multiple course runs listed, one per course, showing the course run which
the user would be enrolled in.


### /api/basket/

This API allows users to interact with their basket to get its status, to update the items
to purchase in the basket, and to add on a coupon.

#### GET

A response would look like

    {
        "items": [
            {
                "id": 3,  // this is ProductVersion.id, not Product.id
                "description": "Supply Chain Management",
                ...and so on. See /api/products above for full schema.
            }
        ],
        "coupons": [
            {
                "code": "DISCOUNT_15_OFF",
                "amount": "0.15",
                "targets": [3]  // ProductVersion.id. There may be more but products not already in cart will be filtered out.
            }
        ]
    }

An empty basket would return:

    {
        "items": [],
        "coupons": []
    }

#### PATCH

A user can PATCH the basket to update the items list or to attempt to use a coupon. Each
time a user PATCHes this endpoint, the basket will be validated. If the basket is not valid
a 400 error will be returned and the basket will be left unchanged.

Also note that a basket passing validation is not a guarantee that the checkout will
pass validation. This could happen if the coupon code was valid when it was being
added to the basket but it was not valid by the time of checkout. A product may also
have its validity changed, preventing checkout from working.

Whatever the request data sent to PATCH, if the response is a success it will contain
the same updated data which GET would return.

TODO: what happens if a basket becomes invalid over time? I think this is somewhat rare
but we should figure out how to handle it. We can just clear the basket but I don't know when
we should do this validation.

##### Clear a basket

A user could clear a basket by patching:

    {
        "items": [],
        "coupons": []
    }

They could clear just the items in the basket:

    {
        "items": []
    }
    
However this would leave the coupon code as is. If there was a coupon code it would
fail validation because there is nothing to apply the coupon to, and the basket would
be left unchanged. So there is no use case for this.

A user could clear only the coupon:

    {
        "coupons": []
    }

However, if there is an automatic coupon which can be applied, it will be automatically
added to the basket even when `coupons` is explicitly set to an empty list.
    

##### Add item to basket

A user could update the basket to have one item by patching:

    {
        "items": [
            {
                "id": 8   // this is ProductVersion.id, not Product.id
            }
        ]
    }
    
Here the coupon is not one of the keys so it would be left as is. However the view
will revalidate the coupon to make sure it can be applied to the new item list. If this
validation fails a 400 response is returned and the basket is left unchanged.

Also note:
 - There is no way to incrementally add items to a basket, leaving existing
items unchanged. The frontend will need to send the complete new list with `id` attributes
for each product. However in practice we will not have more than one item in a basket.
 - At the moment a user can purchase only one item at a time. This will be validated
 on the backend.


##### Add coupon to basket

A user could apply a coupon to a basket:

    {
        "coupons": [
            {
                "code": "DISCOUNT_30_OFF"
            }
        ]
    } 

Existing items in the basket would be left unchanged. The new coupon code would be validated.
If the validation fails a 400 response would be returned and the basket would be left
unchanged.

### /api/checkout/

Unlike MicroMasters there is no payload required for the checkout API. Instead it will
use the user's basket to figure out what should be purchased.

Like edX and MicroMasters, this API will create an `Order` on the backend based on items
and discounts in the `Basket`. The API will return form data which will be used
by the frontend to make an HTML form to be submitted to CyberSource Secure Acceptance.

The frontend will also add certain hidden fields to this HTML form like credit card number
and address so that the user doesn't have to enter them at CyberSource
and we have more control over the UI. Note that these fields will not be sent to our
own server because avoiding handling sensitive information makes PCI compliance simpler.

Some fields will be signed on the backend, for example price, so that the frontend logic
cannot modify this. This is also similar to how edX and MicroMasters work.

TODO: Does paypal support complicate anything here?

#### POST

### /api/order_fulfillment/

This API is for CyberSource only. It allows CyberSource to communicate that an order was
successfully paid for, or that payment failed for some reason. The request data is
signed by CyberSource and this API will verify the signature before processing the message.

For more information read the CyberSource documentation here: http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_Hosted_Checkout/Secure_Acceptance_Hosted_Checkout.pdf

#### POST

CyberSource will POST to this API with fields defined in the CyberSource document. See "Reply Fields"
in Appendix A of the documentation (see link above). In addition to information about the
status of the payment, this payload also includes the request data, prefixed with `req_`.

If the signature verification succeeds the API will first record the whole payload to a
`Receipt` instance. Then it will parse the reference id which we provided earlier
to get the order primary key so it can link the `Order` with the `Receipt`. Then
the `Order.status` is changed to `fulfilled`, or to a different status if there is an
error. Errors will additionally be logged so that this is reported to Sentry. 
