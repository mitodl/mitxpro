Release Notes
=============

Version 0.8.0
-------------

- Always show course run selections (#420)
- Fix missing price on product page (#409)

Version 0.7.2 (Released June 10, 2019)
-------------

- Accept product id, not product version id, on checkout page (#429)
- Added register error and denied pages
- Added validation for legal address fields that need it
- Add company to django admin (#445)
- max_redemptions should be 1 for single-use coupons (#417)

Version 0.7.1 (Released June 07, 2019)
-------------

- Add voucher app for course voucher upload and processing
- #157 Serve Catalog Page from Wagtail
- Added forgot password UI
- Check for Hubspot API errors (#396)

Version 0.7.0 (Released June 06, 2019)
-------------

- Implemented bulk enrollment checkout
- Bump djangorestframework from 3.9.1 to 3.9.4 (#414)
- Added template for config change request and PR checkbox
- Bumped drf version
- Integrate HubSpot in HomePage
- add seed resource pages in cms
- Feedback
- Rebase + Migration Conflict Fixes
- Feedback
- Removed unused import
- #155 Integrate Wagtail Routing
- View/edit profile pages (#346)
- Added support for redirect on register existing email
- Add hubspot form in footer
- #383 Add Home Page Instructions to Readme
- Enroll user in edX course runs on order success

Version 0.6.0 (Released May 30, 2019)
-------------

- Fix footer placement
- fix
- initial changes for companies slider
- Added sanctionsLists to the exports request if it is set
- #257: Home Page: Watch Video Button
- #257 Homepage: About MIT xPRO
- fix if only one date available (#382)
- SEO metadata for product pages (#334)
- Additional serializers for hubspot (#347)
- #352 Fix: Set HomePage as Parent of ResourcePage

Version 0.5.2 (Released May 29, 2019)
-------------

- #252 Home Page: Upcoming Courses
- Added workers to pgbouncer
- #250 #251: Home Page Header
- #258 Home Page: Inquire Now
- Trigger hubspot celery tasks where appropriate (#317)
- updated the footer and added links
- #323 Home Page Base
- allow marketing user to add/edit slug for resource pages (#350)
- fix error in console when no notificaiton available (#351)
- Updated login/registration styling
- Enroll/View Dashboard button (#336)
- add support of hub spot subscription.

Version 0.5.1 (Released May 24, 2019)
-------------

- Fixed encrypted response getting ascii-escaped
- add feature site nofication through cms (#309)
- Added hubspot ecommerce bridge (#276)
- Move Header Bundle back to Original Location
- Use query parameters when loading checkout page (#283)
- Fix coupon apply button bug (#296)
- Added SDN compliance api and data model
- Convert Sections to Generic

Version 0.5.0 (Released May 22, 2019)
-------------

- Added recaptcha to register page
- add resource page background image (#304)
- Track enrollment company (#287)
- Fixed dashboard styling again
- #193 Product Page: Subnav
- Updated notebook Dockerfile to be based off correct image

Version 0.4.1 (Released May 17, 2019)
-------------

- Issue #294 Fix Header Navbar Structure
- Additional kwargs, better efficiency for get_valid_coupon_versions query (#243)
- #161 Product Page: More Dates
- Styling for checkout page (#265)
- Renamed BulkEnrollmentDelivery to ProductCouponAssignment
- Misc improvements - fixed dashboard style regressions, handled empty dashboard, added rule to serve course catalog at root route, added enrollment admin classes
- Registration form - Step 2 (#236)
- Don't check CSRF token for index pages (#280)
- #146 Product Page: Faculty Carousel
- #145 Product Page: Learners Carousel
- add google analytics (#261)
- fix static path of banner image (#260)

Version 0.4.0 (Released May 14, 2019)
-------------

- Catalog page design update
- Tasawer/fix build (#262)
- Added user dashboard

Version 0.3.2 (Released May 10, 2019)
-------------

- Redirect users to /dashboard after CyberSource checkout (#234)
- make generic resource page in wagtail (#238)

Version 0.3.1 (Released May 09, 2019)
-------------

- Course run selection UI, various backend changes (#186)
- Registration detail form - Step 1 (#211)
- fix migration dependency after merge (#230)
- #223 add TOS page in CMS (#224)
- #147 Product Page: Courses Carousel
- #143 Product Page: Who Should Enroll
- For Teams Section (#148) (#189)
- Add faqs section (#220)
- CMS page design - What You will learn

Version 0.3.0 (Released May 07, 2019)
-------------

- Move deps into apt.txt so heroku installs them too
- Create new django app and utils for voucher pdf parsing
- update docker compose for local debugging
- Updated travis script section ANSI colors

Version 0.2.2 (Released May 02, 2019)
-------------

- CMS page design - What You will learn

Version 0.2.1 (Released May 02, 2019)
-------------

- Add unique constraints to some models which link other models together (#204)
- Added test script detail to Travis output

Version 0.2.0 (Released April 30, 2019)
-------------

- Added admin-only bulk enrollment form
- Data consent agreement models and API functions (#163)
- -
- changes after suggestion
- changes after suggestion
- Add the tiles on course detail page.

Version 0.1.2 (Released April 26, 2019)
-------------

- Added model for LegalAddress
- Added X-Access-Token header to protect registration API

Version 0.1.1 (Released April 25, 2019)
-------------

- Added a test to verify app.json
- Update basket API to handle courses (#154)
- Update redis (#172)
- Add Course Page Header
- Upgrade some dependencies (#167)

Version 0.1.0 (Released April 23, 2019)
-------------

- Front-end coupon creation (#129)
- Updated OpenEdxApiAuth refresh to account for expiration
- Fix running pytest for a subset of tests that don't create TEST_MEDIA_ROOT
- Checkout page (#108)
- Updated course catalog to match designs and use CMS data
- Update edx configuration docs to match latest setup
- Feedback
- Added settings and documentation to configure logout/login redirects
- seed data updates (#125)
- Switched routes back to "details"
- Added top nav to static pages
- API view for creating coupons (#114)
- Added validation for password length on register
- Added proper login handling of app context
- Rename CouponInvoice and CouponInvoiceVersion models (#115)
- Add thumbnail to basket API, use get_or_create for Basket (#110)
- Bumped djoser to avoid yanked version
- Basket REST API (#97)
- Checkout and order fulfillment ecommerce REST APIs  (#95)
- Added course enrollment button to course detail page
- Added APIs for creating edx api tokens
- Updated README with seed data instructions
- Fixed binding error
- Coupon functions and model changes (#77)
- Move template tag tests out of templatetags module
- Added model for edX tokens
- Fix app.json validity
- Combined auth steps for creating user and setting pw, name
- Bump docker to stretch debian
- Added MAILGUN_SENDER_DOMAIN and removed MAILGUN_URL from required settings
- Add RFC for coupons (#52)
- RFC for ecommerce REST APIs (#86)
- Added API call to create edX user when xpro user is created
- Fixed hijack release redirect url
- Added registration flow
- Ecommerce factories and utility functions (#69)
- Fixed settings tests locally
- Added courseware Django app
- Added login ui
- Add models for ecommerce (#41)
- Added basic course catalog
- RFC: Bot-friendly front-end
- Adding wagtail (#51)
- Added seed data command
- Added redux-query
- Add RFC for ecommerce models (#36)
- Added authentication app
- Added mail app
- Added simple REST API for interacting with course data
- Added course model admin classes
- Added user model, serializer, and read-only api
- Remove tox, move python test and linting to ./travis/python_tests.sh (#44)
- Add rule to serve static files on dev environments (#50)
- Added RFC for Open edX auth integration
- Adding github templates (#43)
- Fixed courses django app
- Updated readme, un-required mailgun vars, added notebook container
- Added initial course models
- RFC for ecommerce infrastructure (#25)
- Added RFC for storing course data
- Fix JS travis builds

