## Title for RFC

ecommerce workflow

#### Abstract

This describes the various states of ecommerce models and where and when we can and cannot
modify data.

#### Product and ProductVersion

A `Product` represents a thing that the end user can purchase. It has a `GenericForeignKey` to
a `CourseRun`, `Course`, or `Program`, representing the enrollment to be purchased. It has a unique
constraint on the content type and content id fields for the `GenericForeignKey`, which means that
a `CourseRun`, `Course`, or `Program` can have only one `Product` associated to it.

`ProductVersion` will be an append-only table containing information about a `Product`. Each row
will have a foreign key to `Product` as well as `price`, `description`, and any other field
which may be added in the future. When an admin makes a change to a product, the admin UI should
add a new row to the `ProductVersion` table for that product. The row with the latest `created_on`
value for a `Product` will be the source of truth for price and description information.

TODO: which objects refer to `Product` and which to `ProductVersion`?

#### Basket and BasketItem

A `Basket` represents the items a user intends to purchase. It has a foreign key to `User`,
the person who is purchasing the items. A `BasketItem` will have a foreign key to `Product`,
another to `Basket` and a `quantity` field.

A basket may have at most one coupon, but for future flexibility this is a many to many relation.
See `CouponSelection` below.

#### Order and Line

An `Order` represents an attempt to purchase some items. It has a foreign key to `User`,
the person who is purchasing the items. 

An `Order` can have several different statuses. At first
it is `created`. Since a user may check out and then decide not to complete the purchase in
CyberSource, orders may remain in the `created` state indefinitely. Only orders with a fulfilled
status should be counted as purchases.

A `Line` is an item in an `Order`. It has a foreign key to the `Order` and to `ProductVersion`. There
is also a `quantity` field.

A basket may have at most one coupon, but for future flexibility this is a many to many relation.
See `CouponRedemption` below.

#### CouponInvoice

A `CouponInvoice` represents the information provided by an admin when they create coupons
through the admin interface. For example:
 - type of coupon (single use coupon code or multi use promo code)
 - number of coupon codes to generate
 - validity date range
 - purchase order number
 - tag and other record keeping information
 - max number of redemptions
 - max number of redemptions for one user (usually just 1)
 - percent off
 - products the coupon can be used with (link via `CouponEligibility` to `Product`)

`CouponInvoice` instances should not be edited because they are the source of truth for discounts.
If an admin user needs to make changes they should
change `enabled` to `false` for each `Coupon` and then create new coupons with the changes.

#### CouponInvoiceVersion

A `CouponInvoiceVersion` is an audit table for `CouponInvoice`. This is also used as the source
of truth for coupon information since this table will not be edited.

TODO: Store data in JSONField or duplicate fields like in `CouponInvoice`?

#### Coupon

A `Coupon` represents a coupon code and has a foreign key to the `CouponInvoice`.
A single `Coupon` could be used by many people
and redeemed many times, depending on the redemption limitations described in `CouponInvoice`.

#### CouponVersion

This is an audit table for `Coupon`. It has a foreign key to `CouponInvoiceVersion`. There won't
be a JSONField storing data since there is just the coupon code field and the foreign key.

#### CouponEligibility

A `CouponEligibility` is a link from a `Coupon` to `Product` describing which product
the `Coupon` applies to. There may be more than one link if a coupon can work with multiple
products.

Unlike in MicroMasters a program coupon will **not** apply to `Course`
or `CourseRun` which have the `Program` as a parent. Instead links to each of the items to be
purchased must be explicitly created.

#### CouponSelection

A `CouponSelection` is a link from a `Coupon` to `Basket` describing the intent of a user to
redeem the coupon on checkout. For right now there should be only
one `CouponSelection` per `Basket` because only one coupon is allowed per purchase.

#### CouponRedemption

A `CouponRedemption` is a link from a `CouponVersion` to an `Order` describing a coupon which was used
in a purchase. Note that because `Order` may not be fulfilled, application code should check
the `Order` status in order to see whether the `Coupon` was actually redeemed or if a redemption
was just attempted.

TODO: There is a race condition when a user uses the last remaining redemption of a coupon on an `Order` but
never pays so the `Order` is not fulfilled. If another user uses the coupon and then CyberSource
fulfills the `Order`, the coupon would be used twice where it could be used only once. What to do about this? 

#### OrderAudit

The `OrderAudit` table will store append-only information about every change made to `Order`. It
stores this information in a JSONField with information serialized from the `Order`, all related `Line`s
and any `CouponRedemption` linked to it. There should be enough information to have a complete
representation of the order for reporting purposes.

#### Receipt

This stores the raw data received from CyberSource. This should have a foreign key to the
`Order`, determined using the reference id passed to CyberSource and received back in the POST body.
If this is missing or invalid the `Receipt` should still be created for debugging and reporting.

## Workflow 

An admin creates 100 coupons through the admin interface. A `CouponInvoice` is created for this info
as well as a `CouponInvoiceVersion`. 100 `Coupon` instances are created with links to `CouponInvoice`.
100 `CouponVersion`s are also created, one for each `Coupon`.

Later, a user clicks on a button to purchase a program or course. This sends a message to our REST API to
put that item in the basket. Any other items in the basket will be cleared first since our UI restricts
how many items can be in the basket. They are directed to the checkout page.

On the backend a `Basket` is created and a `BasketItem` is created for the item to be purchased. The
`BasketItem` will link the `Basket` to a `Product` matching the item to be purchased. 

They paste the coupon code in the checkout page and click submit. The view checks that the coupon
is valid then adds a `CouponSelection` attaching the `Basket` to the `Coupon` matching the code.

The user types in their credit card number and clicks the checkout button.
An `Order` is created. `Line` instances are created matching each `BasketItem` but with a link
to `ProductVersion` instead of `Product`, the most recent instance. `CouponRedemption` is created
linking `CouponVersion` to `Order`, after first checking that redemption is allowed.

The REST API returns some information in a dict, with most fields signed so the user
cannot tamper with the information. The dict is returned in the POST response to the frontend, then the user POSTs to CyberSource.
If the user successfully completes a payment CyberSource will POST back to our order fulfillment
API which will record the response in `Receipt` and change the `Order` status to `fulfilled`. If
the status in the order POST back is not a success, `Order.status` will be `failed`.
 
At some future time we will implement refund handling and this will set the `Order` status
to `refunded`.

##### Edge cases

Once a user checks out and is directed to CyberSource, the basket will be empty. If the user tries to go back they will find their basket to be empty
and they will have to add their items again.

Fixing this complicates the logic significantly, and the UI does not really have a basket, so I'm
ignoring this edge case for now.
