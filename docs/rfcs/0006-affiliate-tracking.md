## Title for RFC

Tracking affiliate links

### Abstract

We are planning to support affiliate links in MITxPRO. This essentially means that we will advertise xPRO on
other websites ("affiliates") and pay them for the inbound traffic under certain conditions. 

### Architecture Changes

The architecture requirements are pretty simple:
1. A new model that keeps track of our active affiliates and their codes
1. A field or model that keeps track of completed orders/payments for users that were initially referred to us by an
   affiliate. 
1. Middleware that adds some data to the session when a request comes in with an affiliate code 
   (e.g.: `xpro.mit.edu/some-course?aid=affiliatecode123`).
1. Order processing logic that adds data to the new field/model described in item (2) when a payment is completed. 

Some additional changes we'll probably want to make:
1. A new BI query, or an update to an existing BI query, that shows the affiliate for each completed order (if the 
   order was completed after the user was linked to xPRO via an affiliate. See item (2) above).
1. An optional setting for defining the expiration of an affiliate link. For example, if a user visits our site from 
   an affiliate link, then completes an order after a significant amount of time has passed, we may not want to 
   associate the order/payment with the affiliate. A setting would be sufficient to define the maximum age. If we decide
   to implement this, we'll need to store the timestamp of the initial visit in the session along with the affiliate 
   code. 

We probably will not need to automate payments to affiliates (at least not to begin with). 

#### Libraries

There are a few open source libraries that address our use case:
- [django-affiliate](https://github.com/st4lk/django-affiliate)
- [django-affiliate-tracking](https://pypi.org/project/django-affiliate-tracking/)
- [django-simple-affiliate](https://github.com/czue/django-simple-affiliate)

There are some issues or outright blockers with all 3:
- `django-affiliate` – This library is abandoned (last commit 5 years ago) and it does not work with Django 2
- `django-affiliate-tracking` – The code does not appear to be hosted in a public repo
- `django-simple-affiliate` - There are no unit tests, there are `print` statements in critical parts of the 
  middleware, there are some possibly-unnecessary assertions, and the last commit was 3 years ago.

#### Recommendation

I've tested `django-simple-affiliate` and it works. It's also incredibly simple. It just defines a small middleware 
function to add the affiliate code and timestamp to the session, and a helper function to pull the affiliate id from 
a request object if it exists. We don't need much more than that. Since we really don't want `print` statements 
littering our middleware, a couple options would be to (a) fork the repo and publish our own package, or (b) just roll 
our own and implement this ourselves. **Given how simple this code is, I recommend that we implement this ourselves**.
