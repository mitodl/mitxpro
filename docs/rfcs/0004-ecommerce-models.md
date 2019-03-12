## Title for RFC

ecommerce workflow

#### Abstract

This describes the various states of ecommerce models and where and when we can and cannot
modify data.

#### Product

A `Product` has a `price`, `description`, and a `GenericForeignKey` `content_object` which can
refer to any Django model instance. An admin user should be able to edit
`description` or `price` without affecting any previous purchase, so we need to also store
this separately when the purchase is made.

#### ProductVersion

.

#### Basket

A `Basket` has foreign keys to an `Order` and a `User`. The `User` foreign key must always exist.

A `Basket` may be editable or not editable, depending on the `editable` boolean field. In general
a `Basket` starts off editable so that the user can add products or a coupon. Then it becomes not
editable once it is passed to CyberSource for payment.

When a `Basket` is editable it should not have a link to an `Order`, and when it is not editable
it should have a link to an `Order`. This makes the `editable` flag a little redundant but this
makes the intent more explicit, and it provides flexibility in the future if we want to change
the logic around when `Order` is created and linked to a `Basket`.

There should be at most one `Basket` for a user which is editable.
This is the user's active basket. If there is no editable `Basket` for the user,
it should be created once the user adds a product or a coupon.

A basket may have at most one coupon. See `CouponBasket` below.

##### Edge cases

Once a user checks out and is directed to CyberSource, the basket stops being editable even if
they haven't actually paid yet. If the user tries to go back they will find their basket to be empty
and they will have to add their items again.

Fixing this complicates the logic significantly, and the UI does not really have a basket, so I'm
ignoring this edge case for now.

#### Line

A `Line` is an item in a `Basket`. It has a foreign key to the `Basket` and to `Product`. There
are also fields for `price_per_unit`, `total_price`, `quantity` and `description`.

While the basket is editable the price fields and description field will be null because this
information will be calculated from the related `Product`. If a product price changes while
the product is in the basket but before the user checks out, they will need to pay the new price.
(This is probably a rare case, especially since the UI has the user checking out at the same
time they add an item to the basket.)

When a user checks out and the basket becomes not editable, the price fields and description field
will be updated with information from the `Product`. This information is copied so that modifications
of the price and description of the `Product` will not affect the recorded order.

#### Order

An `Order` is created when the user checks out. It can have several different statuses. At first
it is `created`. Since a user may check out and then decide not to complete the purchase in
CyberSource, orders may remain in the `created` state indefinitely.

When a user checks out, they will click a button indicating this in the UI. The `Order` is created
and attached to the user's basket. The basket is made not editable and fields are filled out
with price data. This information is then put into a dict, with most fields signed so the user
cannot tamper with the information.

The dict is returned in the POST response to the frontend, then the user POSTs to CyberSource.
If the user successfully completes a payment CyberSource will POST back to our order fulfillment
API which will record the response in `Receipt` and change the `Order` status to `fulfilled`. If
the status in the order POST back is not a success, `Order.status` will be `failed`.
 
At some future time we will implement refund handling and this will set the `Order` status
to `refunded`.

#### Coupon

A `Coupon` represents a coupon code and stores information about what kind of discount and
to what product it can be applied. A `Coupon` may be used multiple times by multiple people,
depending on the type of coupon.

Once a `Coupon` is created it should **not** be edited. Unlike a `Product`, it is not expected
that admins will edit fields of a `Coupon`. This is because a `Coupon` will be linked to from
a `Basket` via `CouponBasket` and it provides information about the discount given to a user
when they completed an order. `CouponBasket` and `CouponProduct` should also not be edited for
the same reason.

If an admin needs to update `Coupon` information it's recommended to set `enabled` to False on
the existing coupons, then create new `Coupon`s to use instead.

It has these fields:
 - `coupon_code` - a unique string to be used by the end user
 - `max_users` - Maximum number of users who can user the coupon
 - `max_redemptions_per_user` - Maximum number of coupon redemptions per user. 
 - `amount_type` - percent or fixed price discount
 - `amount` - The amount of discount provided, depends on `amount_type`.
 - `enabled` - If false, the coupon is not redeemable
 - `expiration_date` - The latest time a coupon can be redeemed
 - `activation_date` - The earliest time a coupon can be redeemed
 
#### CouponProduct

A `CouponProduct` is a link from a `Coupon` to `Product` describing which products the `Coupon`
applies to. Unlike in MicroMasters a `Coupon` to a `Program` will **not** apply to `Course`
or `CourseRun` which have the `Program` as a parent. Instead links to each of the items to be
purchased must be explicitly created.

#### CouponBasket

A `CouponBasket` is a link from a `Coupon` to `Basket` describing the intent of a user to
redeem the coupon on checkout (or that they already did). For right now there should be only
one `CouponBasket` per `Basket` because only one coupon is allowed per purchase.

### Audit tables

#### OrderAudit

The `OrderAudit` table will store append-only information about every change made to `Order`. It
stores this information in a JSONField with information serialized from the linked `Basket`, each
linked `Line`, and the `Coupon` used if any. There should be enough information to have a complete
representation of the order for reporting purposes.

Note that the `Order`, `Line` and `Coupon` tables should also keep accurate information
suitable for reporting purposes. `OrderAudit` is meant to be a backup copy.

#### CouponAudit

This is the audit table for `Coupon`. It will also store information about each related
`CouponProduct` in its JSONField.

#### Receipt

This stores the raw data received from CyberSource.
