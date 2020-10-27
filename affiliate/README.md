# Affiliate Tracking

This app supports the tracking of affiliate links to xPRO. The basic idea is that we 
advertise xPRO on other websites ("affiliates") and pay them for the inbound traffic under 
certain conditions. 

### Scenarios

We intend to credit our affiliates for traffic if they refer a user to us, and the user 
does one of the following:

1. Creates a new account
1. Completes an order

A database record is created when the app detects that any of the above scenarios has occurred. We can then
run a BI query that creates a report showing what we owe each affiliate based on those records. 

### Implementation Details

The app will create a database record for those user actions under the following conditions:

- The user first arrives on the site with a querystring parameter that has an affiliate code (`?aid=<affiliate-code>`).
- The above code matches the affiliate code for an affiliate in our database.
- The action is completed before the session expires.
  - We store the affiliate code in the session when the user arrives on the site with the affiliate querystring param.
  - Django's default session expiration period is 2 weeks.
- For account creation, the user verifies their email address and completes at least the first page of personal details.
- For order completion:
  1. The order is fully paid for via enrollment code, or the Cybersource transaction completes successfully;
  1. The user does not log out in the period between arriving on the site with the affiliate querystring param and 
     completing the order (logging out flushes the session, which will clear the affiliate code).
