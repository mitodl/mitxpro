## Title for RFC

coupons

### Abstract

This describes the various kinds of coupons and how they will be implemented.

Note: For this RFC the "next" course run is the course run which the user would be enrolled
in when they enroll in a course, whether it is currently running or will run soon.

##### Discount

Coupons may have a percent discount. There is no fixed discount use case at the moment.

##### Cart

There can only be one coupon per cart, and a user may add only one course or one program
to a cart. This simplifies the UX and means we don't need to consider how multiple coupons
can conflict.

Users ultimately purchase course runs. In the UI when a user buys a course it will add the
next course run to the cart. When a user buys a program it will add the next course run 
for each course to the cart.

##### Coupon target

Coupons may apply to programs, courses, or course runs. The logic for what targets a coupon
is redeemable for is different from MicroMasters.

TODO: skip course run coupons for now given no use case?

A program coupon is redeemable only if
all courses for the program are in the cart. If a course was missing from the cart, maybe
because the program is nearing end of life and one of the courses is not enrollable anymore, then the
program coupon would not be redeemable.
  
A course coupon would be redeemable only for the next course run for that course.

Note that the UI will not include a cart, the cart will only be in the backend. The end user
will only be able to buy one course or one program at a time, and can apply only one coupon.
This should simplify the UX for redeeming coupons.

##### Number of redemptions

Coupons have a limited number of total redemptions. They cannot be unlimited to ensure that
there's a cap on the number of discounts applied.

A coupon may be used by any number of users as long as there are redemptions left.

##### Validity

Coupons can be enabled or disabled via a field, or enabled only for a certain period of time.
If a coupon was not enabled at the time of purchase it would not be redeemable for anything.

### Use cases

#### One time use coupons

We ask the admin page to generate 1000 coupons for a course and we email learners individually
with the coupon code. It is a percent discount for one course.

##### Named coupons

A coupon is distributed widely with a special name, for example `MARCHMADNESS15` to get 15%
off. The coupon could be used by an unlimited number of users and has a very high number of
redemptions.

TODO: would this kind of coupon apply to any course in a program, or would each course
get its own coupon code?

##### Automatic program discount

A user buys a program and gets 15% off per course. The coupon is automatically
applied at checkout. They will not be able to apply a second coupon on top of this.

The UX for this should work fine because we only plan to actually provide coupons for
individual courses. So there would not be a coupon that would work for a program level discount,
other than the one automatically applied.

### Reporting

All coupon information needs to be reportable so that staff can see what discounts were
applied to a product and from what coupons. There should be an audit table for `Coupon` and
similar tables, and `Order` audit information should include what coupons were redeemed for that
purchase.

In addition to keeping track of coupons, we also need to keep track of the information
provided when coupons are created, for example the PO number. Ideally the admin should
use a form to create coupons which validates this record keeping.
