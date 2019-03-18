## Title for RFC

coupons

### Abstract

This describes the various kinds of coupons and how they will be implemented.

Note: For this RFC the "next" course run is the course run which the user would be enrolled
in when they enroll in a course, whether it is currently running or will run soon.

##### Discount

Coupons may have a percent discount. There is no fixed discount use case at the moment.

##### Basket

There can only be one coupon per basket, and a user may add at most only one course run,
course, or program to a basket. This simplifies the UX and means we don't need to consider
how multiple coupons can conflict.

Users ultimately purchase course runs. In the UI when a user buys a course it will add the
next course run to the basket. When a user buys a program it will add the next course run 
for each course to the basket.

##### Coupon target

Coupons may apply to programs, courses, or course runs. The logic for what targets a coupon
is redeemable for is different from MicroMasters.

A program coupon is redeemable only if all courses for the program are in the basket. If a course
was missing from the basket, maybe because the program is nearing end of life and one of
the courses is not enrollable anymore, then the program coupon would not be redeemable at all.
  
A course coupon would be redeemable only for the next course run for that course. It may have 
multiple courses where it can be redeemed.

A course run coupon is redeemable only for the particular course run.

Note: The UI will not include a basket, the basket will only be in the backend. The end user
will only be able to buy one course or one program at a time, and can apply only one coupon.
This should simplify the UX for redeeming coupons.

##### Number of redemptions

Coupons have a limited number of total redemptions. They cannot be unlimited to ensure that
there's a cap on the number of discounts applied.
However this could be a very high number, higher than is likely to ever be redeemed.

A coupon will also have a limited number of redemptions per user. Most coupons will only allow
one redemption per user. Automatic program discounts will have the number of redemptions per user
be the same as the total number of redemptions.

A coupon may be used by any number of users as long as there are redemptions left.

##### Validity

Coupons can be enabled or disabled via a field, or enabled only for a certain period of time.
If a coupon was not enabled at the time of purchase it would not be redeemable for anything.

A coupon may also become invalid if the related product is not available anymore.

### Use cases

#### One time use coupons

An admin generates 1000 coupons for a course and we email learners individually
with the coupon code for that user. It is a percent discount for one course, course run, or program.

##### Named coupons

A coupon is distributed widely to the general public with a special name,
for example `MARCHMADNESS15` to get 15% off. The coupon would have a very high number of
redemptions.

The admin would select the courses which this coupon would apply to. The coupon would work
with any of these courses, but the user would only be able to redeem the coupon for one of the courses.
The coupon would not be redeemable for that user for the second time.

##### Automatic program discount

A user buys a program and gets 15% off for each course. The coupon is automatically
applied at checkout. The user may still apply another coupon at their preference but it would
replace the automatic coupon, it would not combine with it.

The UI will show the automatic coupon differently than a manually applied coupon. For the automatic
coupon case it will show the coupon being applied and a text field with text explaining to the user
that the coupon would replace the automatic one.

### Reporting

All coupon information needs to be reportable so that staff can see what discounts were
applied to a product and from what coupons. There should be an audit table for `Coupon` and
similar tables, and `Order` audit information should include what coupons were redeemed for that
purchase.

In addition to keeping track of coupons, we also need to keep track of the information
provided when coupons are created, for example the PO number. The admin should
use a form to create coupons which validates this record keeping.
