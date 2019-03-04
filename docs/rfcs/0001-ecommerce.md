## Title for RFC
ecommerce in mitxpro


#### Abstract

In MicroMasters we made some decisions about ecommerce. This RFC looks
at the decisions made in MicroMasters and those made for edX's ecommerce
stack and makes recommendations for ecommerce in mitxpro.

#### Payment Processors

The only supported payment processor for MicroMasters is CyberSource.
At the time MIT didn't support other payment processors
like Stripe for example, and I believe that's still true today.

edX has support for multiple payment processors, for example 
the [CyberSource payment processor backend](https://github.com/edx/ecommerce/blob/master/ecommerce/extensions/payment/processors/cybersource.py#L369).
This adds some complexity since there are significant differences
between how they interact with the web application's frontend and backend.

##### Recommendation

Unless MIT will support other payment processors in the near future, we should
design to use CyberSource similar to what we do in MicroMasters.

#### Models

MicroMasters only allows a user to purchase one course at a time so there
is no concept of a cart or basket. In MicroMasters the `Order` object stores
the information about the order and has a foreign key to `Line` to store
information about multiple purchased items. However since the user can only purchase one course at
once, there is only one `Line` per `Order` in MicroMasters.

It's a requirement for mitxpro to support multiple items per order so we'll need a cart or basket
for the user to keep track of their order. edX uses a `Basket` object for this purpose, which subclasses
the `AbstractBasket` class from django-oscar. When a user clicks the button to verify a course, they
are redirected to the `basket/add/?sku=SKU` URL which is handled by django-oscar to add the
item to the basket.

##### Recommendation

Whether or not we want to use django-oscar, we will need models like these (using django-oscar names here):
 - `Order` for an instance of a purchase. This should have a `type` field to distinguish purchase orders
 and end user purchases.
 - `Basket` for a user's shopping cart. This should be connected to `Order` and also `User` for
 the user who is making the purchase.
 - `Line` for an item in an `Basket`
 - `Receipt` to store CyberSource post-back information. Foreign key to `Order`.
 - `Product` to represent a purchasable item. In MicroMasters we skip this and 
 instead set the course key in the `Line` directly but should have this object
 to provide future flexibility and to let us decouple the price and the course information.
 - `Coupon` to describe a coupon and how it can be used. This should have at least a field to store the coupon code
and the number of allowed redemptions if a coupon code can be used by multiple users or multiple times.
 - `CouponBasket` to connect `Coupon` with `Basket` to describe where a coupon is being redeemed.
 - `PurchaseOrder` to store notes and other information about a purchase order. Foreign key to `Order`.
A future RFC will define this further.

These tables will have audit tables to record changes in an append-only JSON format similar to
how audit tables are implemented in MicroMasters: `Order`, `Coupon`, `PurchaseOrder`, `Product`. The
`Order` audit table will also save `Basket` and `Line` data which is related to the `Order`, similar to how this works in MicroMasters.

Note that since these audit tables are implemented in Python, we will need to be careful about updating them
with `save_and_log` in whatever interface or view that is provided to edit the tables.

#### django-oscar

edX builds off of many of the abstract models that django-oscar provides, and they also subclass
some of the django-oscar views. It makes sense to ask if we want to make use of these models, views or
other functions rather than rolling our own like we did with MicroMasters.

I think the big question is whether there is any functionality that could be useful and if using it saves times compared
to rolling our own ecommerce infrastructure like we do on MicroMasters. While edX makes extensive use of django-oscar,
they also have a lot of code which is written on top of django-oscar to handle their cases.

##### Recommendation

We decided to not use django-oscar because it doesn't provide enough additional functionality
over writing our own models and logic like we did in MicroMasters.

#### Purchase Orders

In addition to allowing end users to purchase courses, our solution will also
need to handle purchase orders for bulk purchases. We should make sure to record this information
in the same place that we record purchases via CyberSource so that it's simple to create reports from
the information.

We didn't add any support for purchase orders to MicroMasters. I think we manually added information
via Django shell to the `Order` model. We will need an admin site to allow admins to fill in purchase
order information so that they don't manipulate these models directly.

##### Recommendation

A future RFC will define the models and interface for adding purchase orders.

#### Coupons

edX overrides the django-oscar `Voucher` class to support coupons. They have several 
different variations of coupons, for example:

 - who can redeem: once by one user, once by many users, many times by many users
 - discount: fixed discount or percent discount
 - target: verified seat or audit in a course (or something else?)
 - time of validity

edX only allows one coupon to be used at checkout so they don't need to worry about order of operations
when two coupons are applied. There is an admin site which allow admins to generate a CSV of coupon codes,
and to create program offers, enterprise coupons and other kinds of offers. (I'm not sure how the others are used
within edX.)

In MicroMasters we had a custom implementation of coupons, working alongside a custom implementation of financial aid.
The Django admin is used to create coupons and to record information about coupon invoices for bulk instances of
coupons. 

There are variations of coupons in MicroMasters:

 - standard or discounted_previous_course: The latter handles a special case where people who already paid for
 a previous course on edX get a discounted rate.
 - discount: price discount, percent discount, or just set a new price.
 - target: either program or course
 - time of validity

If a coupon is `standard`, the user "attaches" it by clicking on a link in an email. This directs
them to a page and the code is taken off the URL and sent to the server. This creates a `UserCoupon`
object to connect them to the coupon. After an order is created (before it is fulfilled) it
creates a `RedeemedCoupon` to mark that the user is intending to make use of the coupon. When
CyberSource posts back with the success message, this marks the `Order` as fulfilled and also
marks the `Coupon` as having been used. The logic for figuring out if, when and where a coupon
can be used is in `ecommerce.api`.

##### Recommendation

Whatever coupon system we use or come up with, we should assume one coupon per basket and that
every coupon has a coupon code. This greatly simplifies the logic and workflow. If a user
has two coupons to choose from they would need to determine which is best for their particular
purchase.

We also may need to support automatic discounts in the future
based on arbitrary criteria, to be defined. It would be ideal to support this use case using
coupons, given to the user and used explicitly like other coupons.
 
#### Frontend/Backend work

In MicroMasters, when the user clicks the button to submit the order, it creates an unfulfilled order on the backend
and returns a payload with signed fields to the frontend. The frontend then uses that payload to
POST to CyberSource SecureAcceptance, redirecting the browser there. Part of the payload includes
the return URL where the browser polls the backend and shows a success message once CyberSource
posts back and fulfills the order (this is usually pretty quick).

edX works almost exactly the same way for the CyberSource payment processor, since MicroMasters
adapted this workflow in the first place.

If we use django-oscar we have the option to use the HTML forms provided by it, or to
use django-oscar-api for the REST API, or to create our own APIs to work with the models. The
advantage to creating our own APIs is easier integration with the rest of our frontend code, and
easier testing.

##### Recommendation

We will need some REST API to allow users to add items to their basket, whether that comes from
django-oscar-api or if we write our own. We will need to write an API to handle checkouts
(probably adapted from MicroMasters).

If we use the checkout form from django-oscar we will need to do extra work to theme it and
tie in the Javascript to their form to do the CyberSource checkout. I feel like we should write
our own checkout page instead so we have more control over the presentation and so testing
is easier.

#### Security Considerations

We should consider the roles of people who are allowed to create products, coupons, and purchase
orders. We could do three different levels of permissions for this, or to have all of this done
by someone who has an expansive set of permissions.

In MicroMasters the staff user has permission to make all of these changes. This might be
appropriate for mitxpro since it's also managed by MIT and won't have the variety of courses
that edX.org has.

#### Testing & Rollout

In MicroMasters we have a selenium test which works through a $0 purchase, to skip CyberSource. We
can do something similar for mitxpro but for the most part I think unit tests would work fine for us. edX
has a combination of both.
