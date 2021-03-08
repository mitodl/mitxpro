Release Notes
=============

Version 0.78.1 (Released March 08, 2021)
--------------

- HotFix (#2141)

Version 0.78.0 (Released March 03, 2021)
--------------

- Updated compliance email recipient (#2140)
- fix course order in carousel w.r.t position_in_program (#2136)
- Fixed wagtail admin pages list ordering (#2138)

Version 0.77.1 (Released March 01, 2021)
--------------

- update email receipts for checkout purchases (#2129)
- asadiqbal08/Receipt Updates Front end changes. (#2125)

Version 0.77.0 (Released February 24, 2021)
--------------

- Added country name in compliance admin (#2131)

Version 0.76.2 (Released February 16, 2021)
--------------

- Show appropriate messages on Registration Confirmation link failure (#2117)
- Add news and events carousel (#2111)
- fix: filtering user on the basis of username because of non-masters courses (#2118)
- Bump cryptography from 3.2 to 3.3.2
- Replace Font-Awesome & Icomoon with Google Font
- Fix basket sentry errors
- Bump httplib2 from 0.18.0 to 0.19.0

Version 0.76.1 (Released February 11, 2021)
--------------

- Lower coverage requirements to fix flakiness
- Fix product_page JS rendering issue (#2109)
- adding logout redirection (#2103)
- Fix Flaky Tests (#2102)

Version 0.76.0 (Released February 04, 2021)
--------------

- add test coverage threshold (#2098)
- Allow only positive values on price and course count External Course/Program (#2099)
- Allowed username update in admin with warning
- using module level lodash imports (#2091)
- Set inline styling bourdaries and default lazy tag in img elements
- Merge 3rd-party & django js files, Move HTML scripts to js files

Version 0.75.0 (Released January 27, 2021)
--------------

- Ignore B2B line sync errors in hubspot (#2078)

Version 0.74.3 (Released January 22, 2021)
--------------

- Fixed broken JS-based interactive elements on product page
- Combined and reduced font imports, delayed loading non-essential fonts

Version 0.74.2 (Released January 22, 2021)
--------------

- defering possible js and css files (#2072)

Version 0.74.1 (Released January 19, 2021)
--------------

- External/3rd Party Programs (#2062)
- Fixed error handling to save enrollments on edX HTTP errors

Version 0.74.0 (Released January 13, 2021)
--------------

- Bump lxml from 4.3.4 to 4.6.2
- Added optional auth code column to refund spreadsheet
- Enable pylint in sheets/api.py (#2055)

Version 0.73.0 (Released January 12, 2021)
--------------

- Added fields validation on user profile first & last name (#2041)
- Added Wagtail admin API test
- Added Viewset routing for wagtail hook
- adding max_redemption_per_user feature for promo coupons (#2017)
- Upgraded wagtail to 2.9.3, added image rendition caching

Version 0.72.0 (Released December 23, 2020)
--------------

- Peg faker at 5.0.1 to avoid test failures (#2039)

Version 0.71.0 (Released December 21, 2020)
--------------

- Bump ini from 1.3.5 to 1.3.7 (#2031)

Version 0.70.1 (Released December 11, 2020)
--------------

- Fixed 404/500 error with missing course thumbnails

Version 0.70.0 (Released December 09, 2020)
--------------

- Migrate from travis to github actions (#2024)
- Use update user's name api from edx-api-client instead (#2015)

Version 0.69.1 (Released December 07, 2020)
--------------

- Added far-future cache control header to wagtail images

Version 0.69.0 (Released December 02, 2020)
--------------

- Updated sheets readme with apps script failure details
- Added API and command to sync enroll code assignment sheets
- enhance users_api-me  api tests (#2014)
- Switched to mitol.common.envs
- Updated sheets readme with more troubleshooting

Version 0.68.0 (Released November 25, 2020)
--------------

- Disable zap scan (#2002)
- enroll button design fixes

Version 0.67.2 (Released November 24, 2020)
--------------

- Add git ref to Github action 'uses' specifier (#1999)
- Rename ZAP Github workflow
- Remove ZAP release tags to get latest vuln definitions

Version 0.67.1 (Released November 19, 2020)
--------------

- Change ZAP security test to run on schedule (#1995)
- Add OWASP ZAP scan (#1993)
- Added handling for redeeming enrollment codes with different email

Version 0.67.0 (Released November 17, 2020)
--------------

- Added enrollment URL column to enrollment code assignment sheets
- change button text from 'apply now' to 'learn more' for external course pages
- Bump cryptography from 2.7 to 3.2
- Added validation for enrollment deferrals to an unenrollable course run
- Added flag to run python tests only without pylint/cov/warnings

Version 0.66.1 (Released November 12, 2020)
--------------

- Fixed flaky course runs test

Version 0.66.0 (Released November 10, 2020)
--------------

- Added task decorator to file watch renewal task and fixed exception handling

Version 0.65.1 (Released October 29, 2020)
--------------

- Improved task execution and added tracking for sheets file watch renewal

Version 0.65.0 (Released October 28, 2020)
--------------

- Added support for affiliate links

Version 0.64.2 (Released October 22, 2020)
--------------

- Synced xpro user name change with edX (#1958)
- prioritize contract_number to be used as payment_transaction

Version 0.64.1 (Released October 20, 2020)
--------------

- fix icomoon svg broken icons

Version 0.64.0 (Released October 20, 2020)
--------------

- fix minimist security alert

Version 0.63.1 (Released October 15, 2020)
--------------

- fix kind-of security alert
- Dependabot alert: Upgraded yargs-parser above 13.1.2 (#1943)
- B2b Bulk Course/Program dates (#1935)
- Added info about setting up Open edX user and token
- Associated order with course enrollment in enrollment command
- Fixed copyright year text and made it dynamic
- fix n+1 queries to optimize the page

Version 0.63.0 (Released October 13, 2020)
--------------

- Improved BulkCouponAssignment admin to be searchable and show timestamps

Version 0.62.1 (Released October 06, 2020)
--------------

- preload icomoon font and some changes for best practices in HTML
- Addressed Gavin feedback: Course ordered list test updated
- Fixed bug where coupon assignment sheets didn't have local DB record
- Added courses list ordering for B2B Bulk order page

Version 0.62.0 (Released September 29, 2020)
--------------

- Fix Order.MultipleObjectsReturned create_enrollment command
- Bump django from 2.2.10 to 2.2.13
- Updated file watch renewal command to allow renewal of all sheets
- B2B/Bulk: Update coupon payment name to fix name collisions
- Updated the terms & condition text and link url
- Home page performance tweaks - #1908
- Addressing Sam's Feedback

Version 0.61.1 (Released September 10, 2020)
--------------

- clarify management command (#1909)

Version 0.61.0 (Released September 09, 2020)
--------------

- pad short username
- change b2b order coupon name
- fix email change confirmation
- Updated instructions for Programs, Program Runs, Courses, and Course …
- Do not select past dates for course runs

Version 0.60.2 (Released September 04, 2020)
--------------

- Sorting pages in CMS admin by title - #171

Version 0.60.1 (Released September 01, 2020)
--------------

- Product page microdata

Version 0.60.0 (Released September 01, 2020)
--------------

- B2B/Bulk: Add Instructions to downloadable enrollment sheet and remove enrollment code column
- remove underline from notification cross button

Version 0.59.2 (Released August 27, 2020)
--------------

- Simplified product API

Version 0.59.1 (Released August 25, 2020)
--------------

- Upgrade jquery to 3.5.1 - #1863
- apply coupon automatically on switching product from the select field
- certificate layout: line up signatures and their underlines

Version 0.59.0 (Released August 24, 2020)
--------------

- Links in site notification with same color
- Send IP address to cybersource
- Only retry enrollments for active users
- Bump wagtail from 2.7.1 to 2.7.4

Version 0.58.2 (Released August 24, 2020)
--------------

- Bump lodash from 4.17.15 to 4.17.19

Version 0.58.1 (Released August 19, 2020)
--------------

- sync with existing user if exists (#1864)

Version 0.58.0 (Released August 19, 2020)
--------------

- Add the Accessability link in footer

Version 0.57.2 (Released August 13, 2020)
--------------

- Change recaptcha domain (#1861)
- Bump serialize-javascript from 2.1.2 to 3.1.0
- Fixed bug b2b coupon applied to all products - #1844
- Bump httplib2 from 0.14.0 to 0.18.0

Version 0.57.1 (Released August 06, 2020)
--------------

- 1850 inconsistent behavior on bulk purchase page
- Removed redundant sheets dev documentation
- Fixed Drive folder details in sheets dev setup readme
- B2B/Bulk: Automatically Apply Coupon Codes Passed in URL
- Bump elliptic from 6.4.1 to 6.5.3
- Bump codecov from 3.6.5 to 3.7.1
- Bump jquery from 3.4.1 to 3.5.0

Version 0.57.0 (Released August 04, 2020)
--------------

- Add dates to bulk purchase for programs - #1669
- Added developer readme for sheets feature
- Refactor sheets handlers

Version 0.56.2 (Released July 30, 2020)
--------------

- Fixed case-sensitivity bug with coupon assignment sheets

Version 0.56.1 (Released July 30, 2020)
--------------

- Fix hubspot b2b product sync id (#1836)
- updated pillow version

Version 0.56.0 (Released July 30, 2020)
--------------

- precommit hook configuration (#1760)
- Changed email matching in coupon assignment to case-insensitive + updated columns when coupons assigned
- create_enrollment command create an order
- make create, defer, transfer and refund enrollment commands atomic with the edX enrollments
- allow b2b coupons to be used multiple times and with any product

Version 0.55.0 (Released July 27, 2020)
--------------

- Make sure B2BOrders have unique integration ids (#1827)
- Fix undefined error for hbspot
- Update the purchase link to support URL parameters and save data properly
- More PR feedback
- PR feedback
- Added sheets feature runbook

Version 0.54.1 (Released July 17, 2020)
--------------

- Fix for product_id as text during coupon redemption

Version 0.54.0 (Released July 15, 2020)
--------------

- Fix various build/run issues

Version 0.53.1 (Released July 10, 2020)
--------------

- clean up the certificate page display
- pin isort to fix the build error

Version 0.53.0 (Released July 07, 2020)
--------------

- make 5 signatories for the certificate (#1804)

Version 0.52.0 (Released June 30, 2020)
--------------

- Fix Broken Image
- Removed index/unique constraint google file watch expiration field
- Changed pytest mocker usages to stop using context processors + ignored caniuse-lite warning

Version 0.51.2 (Released May 27, 2020)
--------------

- Bulk purchase: sync with Hubspot

Version 0.51.1 (Released May 19, 2020)
--------------

- Added newrelic to worker processes

Version 0.51.0 (Released May 18, 2020)
--------------

- add course creation runbook (#1754)

Version 0.50.0 (Released May 18, 2020)
--------------

- Filter out old coupon versions (#1773)

Version 0.49.0 (Released May 07, 2020)
--------------

- update kind-of version to 6.0.2

Version 0.48.4 (Released April 27, 2020)
--------------

- change placement of order button on checkout page
- Fix product title/nested sorting on Product API - #146
- Change URL routing to allow for program run ids

Version 0.48.3 (Released April 21, 2020)
--------------

- acorn version bump
- Rename UWSGI_ env vars, remove redundant if-env (#1651)

Version 0.48.2 (Released April 16, 2020)
--------------

- Move static/hash.txt rule before the generic static rule (#1658)

Version 0.48.1 (Released April 16, 2020)
--------------

- Moved test file for cms templatetags
- Remove py-call-osafterfork setting from uwsgi.ini (#1641)
- Added versioned image URL template tag to enable CMS image caching
- Bulk purchase form product alphabetic sorting - #137

Version 0.48.0 (Released April 14, 2020)
--------------

- Filter out course runs with enrollment closed
- remove users from the dataconsentagreement admin page

Version 0.47.1 (Released April 13, 2020)
--------------

- Don't display courses that have ended in Boeing voucher upload
- Fixed Receipt admin class
- Bulk purchase text updates - #136
- Added field to track when file watch requests come in

Version 0.47.0 (Released April 08, 2020)
--------------

- Improve uWSGI configuration (#1616)
- Various admin fixes + timestamped model admin class
- Optimized bulk purchase page
- Program certificate fix for missing enrollment - #126
- Pillow upgrade - #132
- Bump minimist from 1.2.0 to 1.2.3

Version 0.46.1 (Released April 08, 2020)
--------------

- Used dynamic image loading for select CMS pages
- Added support for ignored rows in a coupon request spreadsheet

Version 0.46.0 (Released April 02, 2020)
--------------

- B2B bulk receipt email update

Version 0.45.0 (Released March 30, 2020)
--------------

- Fixed login for users who passed exports but were never activated
- Optimize N+1 queries on admin dataconsentagreement page

Version 0.44.2 (Released March 26, 2020)
--------------

- Reduce redundant queries on templates
- Streamlined Wagtail configuration and seed data provisioning

Version 0.44.1 (Released March 24, 2020)
--------------

- choose an active course run when the current product is expired.
- Add a text-only link in password change email
- Add a text-only link on verification emails
- Fix tracking of course run selections when completing orders
- Utilizing search param in zendesk help widget
- upgrade wagtail to 2.7.1
- Admin: on course and program certificates, show date created and updated

Version 0.44.0 (Released March 17, 2020)
--------------

- Changed enrollment code email text
- Retire users by email address in addition to username
- Bulk purchase: update receipt page
- Choose future program run from catalog instead of active one

Version 0.43.3 (Released March 16, 2020)
--------------

- Pin redis version to 5.0.5 in docker config
- Pin nginx to 1.16.1 in docker config

Version 0.43.2 (Released March 12, 2020)
--------------

- remove SHOW_UNREDEEMED_COUPON_ON_DASHBOARD feature flag

Version 0.43.1 (Released March 11, 2020)
--------------

- Bulk Purchase: change error message to an HREF instead of a MAILTO
- Fixed conflicting ecommerce migration file names
- Added assignment sheet webhook

Version 0.43.0 (Released March 10, 2020)
--------------

- set False as default in include_future_runs
- Global coupons/promos #62
- Optimizing N+1 ORM operations
- apply coupons to all course runs of a course (#1574)
- Suppress system shutdown sentry errors
- add loading spinner to bulk purchase page
- Remove course run expiration dates #76
- Made email search case-insensitive for refunds/deferrals

Version 0.42.2 (Released March 06, 2020)
--------------

- Added RedBeat to handle task scheduling

Version 0.42.1 (Released March 05, 2020)
--------------

- Fixed run_tag data migration
- Integrated program runs for checkout
- Revert "Bulk purchase: update receipt page"
- Bulk purchase: update receipt page
- Split account settings page into two forms

Version 0.42.0 (Released March 03, 2020)
--------------

- Sheets management utils tests
- Moved courses views to v1 directory (+1 squashed commit) Squashed commits: [cf7045d] API v1 routes
- Revert "Revert "Allow Email Change PR #1535""
- Added program runs concept and tracking of program run purchases

Version 0.41.1 (Released February 27, 2020)
--------------

- Fix Checkout page crashes if user has inactive enrollment code
- Fixed enrollment change sheet file watch renewal
- add readable_id in search fiels in course admin (#1563)
- Bump django from 2.2.8 to 2.2.10 (#1541)
- Bump codecov from 3.5.0 to 3.6.5 (#1553)
- Web app should issue appropriate headers for cache management (#1538)

Version 0.41.0 (Released February 24, 2020)
--------------

- Update heroku to Python 3.7
- Added deferral sheet file watch and management command
- Removed course run preselect logic in checkout
- Django admin improvements
- Upgrade postgres version in docker-compose, and update to Python 3.7 (#1551)
- #59 Fix unused coupon banner bug after command create enrollment

Version 0.40.1 (Released February 14, 2020)
--------------

- course run on program checkout page (#1515)
- Change Street Address label (Home or Residential)

Version 0.40.0 (Released February 13, 2020)
--------------

- Revert "Merge pull request #1535 from mitodl/umar/369-allow-email-change"
- #369 allow email change
- fix: currency should have two decimal places
- Users with bad edX auth can complete orders.
- load products on coupon page with visible_in_bulk_form=false
- Remove unused CourseCatalogView (#1524)
- Handle deferrals via Google Sheets
- Fixed flaky bulk enrollment list test

Version 0.39.0 (Released February 10, 2020)
--------------

- make account settings page to a private route
- Fix video on catalog page is wrapping to a new line.
- Pass readable product id to checkout page in URL
- Revert "allow email change"
- Fixed vararg positioning
- Added title for resource pages
- added live check
- Fixed incorrect sheets module reference in tasks
- allow email change
- Fixed bug with column definition for refund request sheet
- Fixed unenrollment email start date text
- Add CEU override for certificates
- Sticky Enroll Button Changes
- initial changes

Version 0.38.2 (Released February 03, 2020)
--------------

- Added refund processing via Google Sheets

Version 0.38.1 (Released January 30, 2020)
--------------

- Add error logging for program orders with no run selections

Version 0.38.0 (Released January 28, 2020)
--------------

- handlebars plus django version update

Version 0.37.0 (Released January 27, 2020)
--------------

- #1277 Static content (JS) via Webpack for Django

Version 0.36.3 (Released January 22, 2020)
--------------

- Allow product_id and CouponCode to be specificed in URL

Version 0.36.2 (Released January 17, 2020)
--------------

- Fixed off-by-one error with coupon assignment sheet enrolled status
- Split sheets app code
- Streamlined failed HTTP response messaging
- Fixed coupon redemption handling to account for non-spreadsheet bulk enrollments

Version 0.36.1 (Released January 15, 2020)
--------------

- Allowed multiple coupon requests with same contract number
- Removed 'get_embed' Wagtail library function tests
- 1385 Management command to create enrollment
- pin the version for freezegun
- Added retry for timed-out Mailgun API requests

Version 0.36.0 (Released January 14, 2020)
--------------

- Fixed sheets app log message interpolation

Version 0.35.3 (Released January 13, 2020)
--------------

- mitxpro-1393 Add contract number to b2b order (#1430)
- Add more fields in address line.
- upgrade autoprefixer to fix builds (#1469)
- #1398 Remove login/register from bulk purchase pages
- Changed default renewal period for Drive webhooks to 12hrs
- Added batch Drive file sharing
- Set coupon assignment sheet cells to protected
- #1418 Fix course run sync from edX

Version 0.35.2 (Released January 08, 2020)
--------------

- Fix coupon success message
- Create a ProgramEnrollment along with ProgramCertificate
- Updated the version of handlebars
- Included user's street address
- Added warning for 'automatic' option in coupon creation form
- update the serialize-javascript
- 1438 display dollars and cents in both email and receipt page

Version 0.35.1 (Released December 30, 2019)
--------------

- Added validation and reporting for emails in coupon assignment sheets

Version 0.35.0 (Released December 26, 2019)
--------------

- add flag for hide/show product in bulk seat page
- #1395 Delay automated certificate creation by a number of hours

Version 0.34.5 (Released December 20, 2019)
--------------

- #1404 display readable id when selecting courseware in cms pages
- #1313 update sync_grades_and_certificates command msg
- MIT xPRO - 1386 Checkout: Display success message when coupon is successful

Version 0.34.4 (Released December 18, 2019)
--------------

- change value of constant (#1414)
- Fixed sheets error handling & management command bugs

Version 0.34.3 (Released December 17, 2019)
--------------

- Added setting for overriding host used in SSL redirect
- Disable server-side cursors by default to avoid invalid cursor errors (#1407)
- optimize repetitive looping on course catalog page (#1291)
- display correct course name over receipt email
- Changed coupon request handling to create unrecognized companies

Version 0.34.2 (Released December 17, 2019)
--------------

- Modified request sheet handling to allow for requester email column
- Fixed bug with updating coupon assignment rows upon enrollment
- Revert "Fixed bug with updating coupon assignment rows upon enrollment"
- Optimized coupon assignment sheets processing to ignore unchanged sheets
- Prevented repeated processing of failed coupon request rows
- Forced spreadsheet file watch renewal in running job
- Fixed bug with updating coupon assignment rows upon enrollment
- Send order receipt email to purchaser
- list unredeemed enrollments on dashboard (#1356)
- Changed assignment sheet title
- add search for courserungrade in admin (#1377)

Version 0.34.1 (Released December 12, 2019)
--------------

- Fixed bug with updating coupon assignment rows upon enrollment

Version 0.34.0 (Released December 12, 2019)
--------------

- #1346 Add receipt link to dashboard
- Set coupon assignment sheet status when coupon is redeemed
- Fixed file watch bug and added management command options
- #1246 sync course runs from edx
- Bump django from 2.2.4 to 2.2.8

Version 0.33.2 (Released December 09, 2019)
--------------

- Send cookie to hubspot when a user creates a new account (#1364)
- Add product_id to hubspot line item (#1366)
- #1345 Receipt Page
- restyle labels on dashboard (#1361)

Version 0.33.1 (Released December 06, 2019)
--------------

- Added spreadsheet sharing error handling

Version 0.33.0 (Released December 04, 2019)
--------------

- Added model and task to manage coupon request webhook
- Added error reporting for coupon request spreadsheet
- Vouchers: seed data for vouchers
- Changed coupon assignment sheet handling to fetch one at a time
- Fixed Google Sheets file watch request

Version 0.32.3 (Released November 25, 2019)
--------------

- Updated Sheets setup doc
- Enabled bulk coupon creation and assignment via Google Sheets

Version 0.32.2 (Released November 21, 2019)
--------------

- Add X-Forwarded-Host setting and make it configurable
- Not check for expired run if there is --force flag

Version 0.32.1 (Released November 19, 2019)
--------------

- TypeError/api/courses/
- #1173 gtm purchase tracking

Version 0.32.0 (Released November 19, 2019)
--------------

- make Firefox Certificate print stylesheet makes page elements identical to Chrome
- - Management Command to revoke courserun/program certificate.
- #1243 Set user context for Sentry

Version 0.31.2 (Released November 15, 2019)
--------------

- update pillow, wagtail
- #1259 Usernamify fix for Turkish characters

Version 0.31.1 (Released November 12, 2019)
--------------

- Filter invalid runs from selected runs list (#1308)

Version 0.31.0 (Released November 12, 2019)
--------------

- fix forgot password form while logged in
- #1267 Configurable CSRF_TRUSTED_ORIGINS env var

Version 0.30.0 (Released November 08, 2019)
--------------

- Add status to deal and line, add birth year to contact

Version 0.29.2 (Released November 07, 2019)
--------------

- #1301 Fix certificate view (4 signatures inline)
- Added setting for controlling edx API client request timeout

Version 0.29.1 (Released November 06, 2019)
--------------

- Added setting for controlling edx API client request timeout

Version 0.29.0 (Released November 05, 2019)
--------------

- #1245 Add search to product and version admin
- Display the text id and price in product list_display
- Vouchers: sort matching courseruns by similarity
- Changed product coupon assignment match to be case-insensitive

Version 0.28.2 (Released November 01, 2019)
--------------

- #1280 External course page apply now button fix

Version 0.28.1 (Released October 31, 2019)
--------------

- #1265 Certificate generation only on passed status
- #1222 Program next run date comes from first course
- #1232 External course CMS page
- #1250 Add SignatoryIndexPage from CMS

Version 0.28.0 (Released October 30, 2019)
--------------

- Changing default database addon to be standard-0 to allow for more connections
- change password form added

Version 0.27.2 (Released October 28, 2019)
--------------

- Design the certificate in print mode.
- fix key error in transfer enrollment command

Version 0.27.1 (Released October 25, 2019)
--------------

- add sorting for all ecommerce adming pages
- Added custom metadata options in mail API and added metadata to bulk enrollment emails

Version 0.27.0 (Released October 21, 2019)
--------------

- Expand clickable area for user menu
- watch now should come only in the presence of video
- #843 Checkout: non-200 responses

Version 0.26.2 (Released October 21, 2019)
--------------

- Filter courses, runs, and programs based on product and live status (#1230)
- - Added the zendesk help widget to project
- Show time along with date for upcoming courses.

Version 0.26.1 (Released October 17, 2019)
--------------

- Updated metadata for new attempt at TLS cert generation

Version 0.26.0 (Released October 16, 2019)
--------------

- add order optional parameter in refund_enrollment command
- Fix the layout issue for IE

Version 0.25.2 (Released October 15, 2019)
--------------

- Add topics to programs API (#1197)
- fix broken commands in readme
- Add course topics (#1196)

Version 0.25.1 (Released October 10, 2019)
--------------

- #1205 certificate button 404 fix
- #1203 Exports inquiry admin action fix
- retire user management command (#1158)
- fix catalog page for IE11
- #1200 Course certificate generation task fix

Version 0.25.0 (Released October 10, 2019)
--------------

- add product as raw_id_field in product version admin page
- add loading indicator on checkout page
- Add instructors to programs API (#1177)
- #978 Admin interface for export compliance result
- - Display account created date and last login date on user admin page

Version 0.24.2 (Released October 08, 2019)
--------------

- Fixed Product admin
- Fixing verification rendering

Version 0.24.1 (Released October 03, 2019)
--------------

- performance optimization on catalog page (#1150)
- Update Forgot Password message
- MIT xPRO - 1063 Fix redirect issue while creating account

Version 0.24.0 (Released October 01, 2019)
--------------

- Changed catalog logic to show courses with past start dates but future enrollment end dates
- Allow anonymous access to course list and detail API (#1161)
- Updated several admin classes (course run enrollment, etc)
- Added bulk assignment CSV download to bulk coupon form

Version 0.23.2 (Released October 01, 2019)
--------------

- Update program serializer (#1155)
- Optimized bulk enrollment form queries
- email verification message updated (#1134)
- ProgramCertificate will not create for standalone course.
- - Introduce FormErrors for ecommerce coupons
- change from email for admin notifications

Version 0.23.1 (Released September 26, 2019)
--------------

- Optimized bulk enrollment form queries

Version 0.23.0 (Released September 23, 2019)
--------------

- Update UI for selecting products in B2B purchase form (#1095)
- Made programs API public and added Program.current_price

Version 0.22.1 (Released September 23, 2019)
--------------

- #1123 certificate validation link
- - Add validation over name field
- Fix migrations by renaming one conflicting migration to happen later
- Change decimal places for amount from 2 to 5 and add validation (#1124)
- - Import the signal in courses app
- Add a "is_active" field to the product model
- Open a fancybox upon clicking on Watch Now button..
- Lowered max username length to 30 (in code, not in db)
- #980 Coupons: product selection improvement
- #1099 Program certificate links and view
- Updated sync_grades_and_certificates params
- Adding validation to proper Nginx config and full HTML response
- Implement discount codes for B2B purchases (#1055)
- Certificates: create program certificate

Version 0.22.0 (Released September 18, 2019)
--------------

- Add payment_type and payment_transaction for coupons created by B2B purchases (#1115)
- Add Order.total_price_paid and populate from coupon discount and product prices (#1111)
- Coupons for refunded orders should not be valid (#1102)
- Remove reference prefix environment variable, use environment instead (#1109)
- Changed username generation to be based on users' full names
- Make text_id a read-only field in django admin (#1105)
- Add explanation text to B2B purchase and receipt pages (#1090)
- Adding TLS verification for Fastly

Version 0.21.0 (Released September 16, 2019)
--------------

- #875 #940 Course Certificates
- Added edX unenrollment capability
- Added cron job to repair courseware users
- - Certificates: automate course certificate creation
- Added cron job to retry edx enrollments
- update js-yaml

Version 0.20.1 (Released September 06, 2019)
--------------

- update set-value and mixin-deep js dependencies
- update eslint utils, fix eslint issues
- styling of file name

Version 0.20.0 (Released September 04, 2019)
--------------

- #595 Sort dashboard courses

Version 0.19.2 (Released September 03, 2019)
--------------

- Add modal selection widget for enrollment code purchase form (#1024)
- - custom lightbox

Version 0.19.1 (Released August 29, 2019)
--------------

- Fixed bug in sync_grades_and_certificates command
- Add id to Hubspot product title (#1053)
- add raw_id_fields to ecommerce django admin (#1056)
- #874 Course run certificate management command
- Set coupon expiration to end of specified day (#1054)

Version 0.19.0 (Released August 28, 2019)
--------------

- Fixed DATABASE_URL inheritance for CI
- Remove B2B order fulfillment API, merge with ecommerce order fulfillment API (#1045)
- Do not check for hubspot errors without an api key (#1048)
- Add checkout URL to B2B enrollment code checkout CSV (#1040)
- link to support center on voucher resubmit page

Version 0.18.2 (Released August 26, 2019)
--------------

- Send email when a B2BOrder is fulfilled (#1003)
- voucher dropdown update (#1042)

Version 0.18.1 (Released August 21, 2019)
--------------

- Updated program API with additional fields

Version 0.18.0 (Released August 20, 2019)
--------------

- Coure/Program Certificate models

Version 0.17.2 (Released August 19, 2019)
--------------

- Add pages for bulk enrollment code purchase and a receipt page to download codes (#958)
- #918 CourseRun Expiration Date

Version 0.17.1 (Released August 16, 2019)
--------------

- Enabled case-insensitive email search in management commands
- Bump js dependencies

Version 0.17.0 (Released August 14, 2019)
--------------

- Added new edX enrollment command options and refactored command helpers
- Bumped django
- Backend work for b2b enrollment code purchases (#977)
- Fixed bug where 'edx_enrolled' flag was not being updated by enrollment commands
- profile.highest_education can be blank but not null (#989)
- Changed edX enrollment mode from audit to professional
- Improved Django admin UI for several coupon-related ecommerce models

Version 0.16.5 (Released August 12, 2019)
--------------

- -fix for program
- Make checkbox CSS rule more specific to catalog page (#969)
- add highest level of education in profile
- Add b2b_ecommerce app to handle bulk enrollment code purchases (#917)
- Include specific libraries which need transpiling (#959)
- Certificate page customization (CMS)
- Send enrollment/unenrollment emails
- Add support for IE11 (#956)
- Fix Safari issue

Version 0.16.4 (Released August 09, 2019)
--------------

- Make checkbox CSS rule more specific to catalog page (#969)

Version 0.16.3 (Released August 08, 2019)
--------------

- Include specific libraries which need transpiling (#959)
- Certificate page customization (CMS)
- Send enrollment/unenrollment emails
- Add support for IE11 (#956)

Version 0.16.1 (Released August 07, 2019)
--------------

- Fix incorrect password redirecting a user to the create account error page
- fix spaces around copoun code

Version 0.16.0 (Released August 06, 2019)
--------------

- Removed un existent field 'description'
- show archive enrollments on dashboard

Version 0.15.2 (Released August 05, 2019)
--------------

- Make voucher search more fuzzy and robust

Version 0.15.1 (Released August 02, 2019)
--------------

- Added explicit buffer size to uWSGI for cookie size issues
- remove redudant code
- js dependencies updated
- #929 Test fixes for program more dates
- Add more information to OrderAudit (#896)
- #679 Set an HTML title on React pages
- #914 Inactive products should not show on catalog
- #783 React should scroll to top on page load

Version 0.15.0 (Released August 01, 2019)
--------------

- Fixed auth flow to support incomplete registrations
- Update JS to fix caniuse-lite warning (#922)
- #882 display more dates on program page
- Added tagging for sentry errors to review apps
- #908 Wagtail admin generated URLs for child pages
- Add staff payment_type to CouponPaymentVersion (#898)

Version 0.14.1 (Released July 26, 2019)
--------------

- Update audit table serialization for program and course run enrollments (#861)
- fix styling on account exists message

Version 0.14.0 (Released July 25, 2019)
--------------

- Django admin for version tables (#830)
- Changed refund command to properly create order audit record
- Move hubspot contact sync task out of atomic transactions (#891)
- Add protection rules for ProductVersion, CouponVersion, CouponPaymentVersion (#795)
- Remove pep8 (#852)
- Use next_run_id for a default for the checkout page course run selection (#856)
- #885 Use catalog_details for featured product card
- disply message when account already exists

Version 0.13.6 (Released July 22, 2019)
--------------

- add heading feidl in who should enroll section

Version 0.13.5 (Released July 19, 2019)
--------------

- Upgrade Python dependencies (#845)
- dont load hero banner video on mobile devices
- - Wrong price for program

Version 0.13.4 (Released July 17, 2019)
--------------

- Update some JS dependencies (#829)

Version 0.13.3 (Released July 17, 2019)
--------------

- change "For Teams" in product subnav to "Enterprise" (#849)

Version 0.13.2 (Released July 16, 2019)
--------------

- Update voucher/templates/enroll.html
- Adjust style and fix typos
- Change voucher page style

Version 0.13.1 (Released July 15, 2019)
--------------

- Change URLs for vouchers to /boeing (#822)

Version 0.13.0 (Released July 15, 2019)
--------------

- Fixed enrollment commands - set order status, changed output (#794)
- fix comparison error when there is not start_data for course run (#836)
- Upgrade Django to 2.2, wagtail to 2.5.1 (#785)
- Used ImageChooserPanel

Version 0.12.3 (Released July 15, 2019)
--------------

- Fix typo with command arg
- Find old vouchers, ensure unique pdf names, add more error logging (#814)
- #792 Featured Product Card Thumbnail Fix
- #776 Allow Mixed Case Section Heads and Subheads

Version 0.12.2 (Released July 12, 2019)
--------------

- Fixed seed data bugs, added products, added deletion command
- Vouchers for django admin (#813)
- Added command to decrypt exports inquiry
- Automate environment variables
- set the background color of menu
- fix color of navigational arrows
- minor scss fixes

Version 0.12.1 (Released July 11, 2019)
--------------

- Update styling of enrolled button and add a check mark (#757)
- Change validation error message to Enrollment / Promotional Code (#797)
- Coerce fields to and from empty strings to fix React uncontrolled warnings (#781)
- new background for faculty section (#779)
- Added config to avoid OSERRORs from uwsgi
- Fix django admin search for CoursewareUser (#773)
- fix styling of header link in mobile view (#799)
- #743 Product page catalog details
- #800 Update Readme regarding index page setup management command
- #742 Learning Outcomes subhead convert to richtext
- fix regex for false positive, add test for invalid codes (#798)

Version 0.12.0 (Released July 09, 2019)
--------------

- Tasawer/fix account creation for Canadian users (#787)
- Upgrade sentry for Python and JS (#771)
- Add notification when user verifies their email (#760)
- update edX devstack installation steps. (#762)
- Coupon form improvements (#737)

Version 0.11.4 (Released July 05, 2019)
--------------

- fix hardcoded product page url (#768)
- Do not include unused_coupons field when syncing contacts to hubspot (#766)
- restyling catalog page to allow featured course (#706)

Version 0.11.3 (Released July 05, 2019)
--------------

- Create 'Coupons' group and additional properties for Hubspot deals (#628)
- Fixed and refactored enrollment commands
- redirect cms login to site signin
- Add text_id to ProductVersion (#692)
- Disable submit button while processing (#725)
- Fixed catalog login/signup urls
- Updating wording on the verification email
- Added catalog link to empty dashboard
- Update tests
- Switch hardcoded url to reverse url

Version 0.11.2 (Released July 03, 2019)
--------------

- Save order on enrollment objects (#676)
- #740 Product Page: Add commas to prices tile
- #739 Remove contractions from subnav
- #738 Remove course position label from product page
- autoComplete attributes for form fields (Chrome) (#730)
- Use site wide notifications for DashboardPage (#701)
- Revert "Remove the old PR template that is hiding the new one"
- Remove the old PR template that is hiding the new one
- Use program.title and run.title instead of product.description (#724)
- #715 Make cms subheads optional
- Added enrollment audit admin classes

Version 0.11.1 (Released July 02, 2019)
--------------

- #726 Remove blog link from footer
- removed phone number from footer

Version 0.11.0 (Released July 01, 2019)
--------------

- Reordered CMS model definitions
- Added 'create account' link to sign in page

Version 0.10.5 (Released June 28, 2019)
--------------

- #704 Watch Now button support for Youtube videos

Version 0.10.4 (Released June 28, 2019)
--------------

- just update the URL
- Fixed margin issue with site-wide notifications

Version 0.10.3 (Released June 27, 2019)
--------------

- Poll dashboard page for course run/program (#678)
- links to web.mit.edu should open in a new tab (#689)
- fix redirect url after signin (#658)
- Tweak notification CSS to prevent video from displaying over notifications (#688)
- Added robots.txt via django-robots

Version 0.10.2 (Released June 27, 2019)
--------------

- Fix header CSS for video on home page (#603)
- Removed links for course runs that have not yet started in edX
- Added course run enrollment email
- Upgraded deps
- Get unused coupons in the UserSerializer instead of CurrentUserRetrieveUpdateViewSet (#667)
- Send email to support when enrollments fail (#634)

Version 0.10.1 (Released June 26, 2019)
--------------

- #659 Catalog: prices are not displayed for some courses/programs
- Add redirect for cancellation and certain merchant fields to CyberSource payload (#604)
- Initial commit
- Remove texts in footer.
- Replace "login" with "Sign in"
- #464 Subnav font style should conform to designs
- Replace "validate" with "verify"

Version 0.10.0 (Released June 25, 2019)
--------------

- catalog page sorting based on start_date
- #610 TemplateDoesNotExist should raise a 404
- #615 Add `live` filter to unexpired course runs
- Remove enableReinitialize, resetForm manually (#637)

Version 0.9.4 (Released June 24, 2019)
-------------

- Proper fix for edx user creation race condition
- Fixed race conditions around user creation and repair scripts
- fix styling of youtube video
- Fixed race condition with AccessToken
- User hubspot-formatted purchaser id in OrderToDealSerializer (#625)
- Convert signout MixedLink to regular <a> tag (#621)
- Fix broken tests for DataConsentUser (#624)
- Clear runs from basket when selected item changes (#569)

Version 0.9.2 (Released June 21, 2019)
-------------

- Renumber migration (#613)
- Make enrollment company blankable in admin (#585)
- User menu (#560)
- Validate data consent agreements have been signed (#580)
- Added enrollment change management commands
- add CatalogPage as subpage to homepage
- add support for youtube videos
- Add hubspot sync all management command and handle line sync errors
- Move sync_hubspot_deal call out of atomic transaction (#571)
- Changed wagtail URLs to use course/program readable id

Version 0.9.1 (Released June 20, 2019)
-------------

- Fix login redirect regression
- Added enrollment change status fields
- Change basket PATCH to use product_id instead of id (#576)
- Add popup for anonymous users to login when they want to enroll (#575)
- Bump django from 2.1.7 to 2.1.9
- Add links to terms of service, privacy policy, refund policy (#525)
- Exclude expired and enrolled runs from courserun dropdowns (#524)
- Layout and wording fixes for register form
- Ensure order of runs is always the same to avoid test flakiness (#557)

Version 0.9.0 (Released June 18, 2019)
-------------

- fix course image thumbnail (#549)
- - link MIT logo in header to web.mit.edu
- Save voucher pdf uploads to S3 (#552)
- Added audit tables for enrollment tables
- - Align dashboard text
- #203 Product Page: fix right margin at 768px
- replace aqua color to more darker color (#529)
- add reply-to email address in emails (#528)
- Data consent checkbox (#519)
- Set checkout page to be accessible only to logged-in users
- fix
- #442 Product Page: Propel your career section
- #448 Courseware: space between text/"view detail"
- add live filter to subpages of home and product pages (#532)
- #466 Catalog: display popover on tab hover
- #468 Footer links should not spawn new tab
- Feedback from Abdul
- #450 Change yellow color because of accessibility
- Fixed site-wide notification styling
- Standardize button text
- updated the style.
- #173 Product page: support HLS video URL in header

Version 0.8.2 (Released June 13, 2019)
-------------

- Added unused coupon reminder alert
- Add enroll/view dashboard button on program page (#495)
- Refactor checkout page to use formik (#435)
- #407 Slick dot should not appear when no scroll
- Fix site  MIT xPRO name everywhere (#488)
- Prevent end users from patching other data consents (#480)
- Disable autoplay/infinite on logos carousel
- replace cost with price.
- #469 Testimonial Carousel Read More Link
- #510 Courseware carousel links not working
- #470 Product page: Subnav scroll fix
- #472 Program Page: don't show "view full program"
- #504 Enroll Now Button Overlapped
- #477 Disable infinite scroll on carousels
- #499 Clicking on Continue Reading Leads to 404
- Store information on voucher redemption and enrollment

Version 0.8.1 (Released June 12, 2019)
-------------

- Expand hubspot settings to sync deal, line, product
- update email template (#487)
- update styling of metadata tiles (#476)
- #428 #447 #448

Version 0.8.0 (Released June 11, 2019)
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

