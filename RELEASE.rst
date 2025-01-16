Release Notes
=============

Version 0.171.0
---------------

- refactor: migrate ENABLE_ENTERPRISE to posthog (#3368)
- refactor: migrate FEATURE_ENROLLMENT_WELCOME_EMAIL to posthog (#3362)
- fix(deps): update dependency django to v4.2.18 [security] (#3376)
- [pre-commit.ci] pre-commit autoupdate (#3374)
- chore: remove ruff (#3375)
- refactor: remove ENABLE_BLOG & WEBINARS feature flags (#3358)
- chore(deps): update dependency ruff to ^0.9.0 (#3373)
- fix(deps): update dependency django-hijack to v3.7.1 (#3372)
- fix(deps): update dependency boto3 to v1.35.97 (#3371)

Version 0.170.0 (Released January 14, 2025)
---------------

- fix: language not available in course draft pages (#3365)
- chore(deps): lock file maintenance (#3366)
- chore(deps): update codecov/codecov-action digest to 1e68e06 (#3364)
- refactor: remove ENABLE_CATALOG_SORTING (#3359)
- refactor: remove ENABLE_EXTERNAL_COURSE_SYNC (#3360)
- feat: Add language support in courses (#3335)
- refactor: remove COURSE_DROPDOWN flag (#3361)

Version 0.169.1 (Released January 08, 2025)
---------------

- refactor: remove ENABLE_TAXES_DISPLAY feature flag (#3354)

Version 0.169.0 (Released January 07, 2025)
---------------

- [pre-commit.ci] pre-commit autoupdate (#3355)
- feat: convert CEUs to decimal (#3217)

Version 0.168.0 (Released January 06, 2025)
---------------

- chore: improve tests execution time for hubspot (#3350)
- revert: node version (#3352)
- fix: npm tests locally (#3351)
- fix(deps): update dependency django to v4.2.17 [security] (#3345)
- fix: replace matchPackages with matchPackageNames (#3343)
- [pre-commit.ci] pre-commit autoupdate (#3344)
- fix(deps): update dependency hls.js to v1 (#3060)
- Add min and max weekly_hours to reflect time_commitment (#3337)
- [pre-commit.ci] pre-commit autoupdate (#3342)
- min_weeks and max_weeks field added to replace duration field (#3336)
- feat: make course searchable in courseRun admin (#3341)

Version 0.167.0 (Released January 02, 2025)
---------------

- feat: How you will learn and B2B section added for external courses (#3318)
- [pre-commit.ci] pre-commit autoupdate (#3338)
- feat: Course overview child page added (#3324)
- fix(deps): update dependency history to v5 (#3262)

Version 0.166.0 (Released December 16, 2024)
---------------

- feat: add Global Alumni in external course sync (#3330)
- [pre-commit.ci] pre-commit autoupdate (#3332)

Version 0.165.0 (Released December 11, 2024)
---------------

- chore: change backend name (#3327)

Version 0.164.3 (Released December 05, 2024)
---------------

- feat: add emeritus api list view (#3329)
- [pre-commit.ci] pre-commit autoupdate (#3326)

Version 0.164.2 (Released December 02, 2024)
---------------

- feat(api): has_prerequisites field added in courses and programs API (#3306)
- Revert "fix(deps): update dependency sass to ~1.81.0" (#3323)
- chore(deps): Remove unused package 'set-value' (#3307)
- perf: select related objects for course and courserun admin (#3316)
- chore(deps): update codecov/codecov-action action to v5 (#3314)
- fix: strip emeritus course title during sync (#3317)
- [pre-commit.ci] pre-commit autoupdate (#3315)
- fix(deps): update dependency sass to ~1.81.0 (#3313)
- chore(deps): update postgres docker tag to v17.1 (#3312)
- chore(deps): update dependency faker to v30.10.0 (#3311)
- fix(deps): update dependency boto3 to v1.35.63 (#3310)

Version 0.164.1 (Released November 21, 2024)
---------------

- chore(deps): update docker.elastic.co/elasticsearch/elasticsearch docker tag to v8 (#3243)
- chore(deps): update node.js to v22 (#3244)
- chore(deps): update dependency normalize-url to v8 (#3240)
- chore: run tests in parallel (#3304)
- chore(deps): update postgres docker tag to v17 (#3198)
- chore(deps): update dependency faker to v30 (#3224)
- chore(deps): update dependency freezegun to v1 (#3236)
- chore(deps): lock file maintenance (#3302)
- fix(deps): update dependency django-hijack to v3.7.0 (#3234)
- chore: remove unused dep mixin-deep (#3303)
- chore(deps): update dependency ruff to ^0.7.0 (#3233)
- fix(deps): update dependency wagtail to v5.2.7 (#3232)
- fix(deps): update dependency boto3 to v1.35.58 (#3230)
- fix(deps): update dependency uwsgi to v2.0.28 (#3231)
- chore(deps): update actions/setup-python digest to 0b93645 (#3225)
- [pre-commit.ci] pre-commit autoupdate (#3229)

Version 0.164.0 (Released November 13, 2024)
---------------

- fix(deps): update dependency psycopg2 to v2.9.10 (#3227)
- fix(deps): update dependency boto3 to v1.35.57 (#3226)
- fix(deps): update dependency zeep to v4.3.1 (#3223)
- [pre-commit.ci] pre-commit autoupdate (#3219)

Version 0.163.2 (Released November 06, 2024)
---------------

- Add a `configure_instance` management command (#3212)

Version 0.163.1 (Released November 05, 2024)
---------------

- refactor: enhance topic assignment command to ignore course pages without course (#3220)

Version 0.163.0 (Released November 05, 2024)
---------------

- feat: add management command for course/topics assignment (#3216)

Version 0.162.0 (Released October 31, 2024)
---------------

- fix: allow only sellable product creation (#3211)
- [pre-commit.ci] pre-commit autoupdate (#3213)
- [pre-commit.ci] pre-commit autoupdate (#3209)
- feat: add posthog integration (#3207)

Version 0.161.1 (Released October 23, 2024)
---------------

- refactor: remove extra condition on Catalog card Next Run Date (#3208)
- chore(deps): update redis docker tag to v7

Version 0.161.0 (Released October 15, 2024)
---------------

- fix: html templates script issue (#3205)
- Revert "fix(deps): update dependency sass to ~1.79.0" (#3203)
- fix: coupon code download view permissions (#3201)
- chore(deps): update actions/setup-python action to v5 (#3197)
- feat: add coupons deactivate form (#3160)
- fix(deps): update dependency unzipper to ^0.12.0
- fix(deps): update dependency sass to ~1.79.0
- fix(deps): update dependency boto3 to v1.35.39
- fix: docker compose version warning and remove travis (#3189)
- deps: remove drf-flex-fields (#3192)
- fix(deps): update dependency user-agents to v2.2.0 (#3190)
- chore(deps): lock file maintenance (#3188)
- fix(deps): update dependency uwsgi to v2.0.27 (#3185)
- chore(deps): update node.js to v20.18.0 (#3186)
- fix(deps): update dependency xmltodict to ^0.14.0 (#3187)
- fix(deps): update dependency boto3 to v1.35.37 (#3184)
- chore(deps): update nginx docker tag to v1.27.2
- fix(deps): update dependency @sentry/browser to v7 [security] (#3173)
- chore(deps): update akhileshns/heroku-deploy digest to e86b991 (#3181)
- fix(deps): update dependency django-hijack to v3.6.1 (#3180)
- fix(deps): update dependency boto3 to v1.35.36
- [pre-commit.ci] pre-commit autoupdate (#3178)

Version 0.160.6 (Released October 10, 2024)
---------------

- feat: skip non usd emeritus courses (#3174)

Version 0.160.5 (Released October 07, 2024)
---------------

- style: add trademark logos (#3176)

Version 0.160.4 (Released October 07, 2024)
---------------

- [pre-commit.ci] pre-commit autoupdate (#3171)
- fix: changed the default value of sorting featureflag (#3172)
- feat: add catalog filter feature flag (#3167)
- fix(deps): update dependency boto3 to v1.35.29

Version 0.160.3 (Released September 27, 2024)
---------------

- fix: display homepage topics with courses (#3166)

Version 0.160.2 (Released September 25, 2024)
---------------

- fix: handle tampered queryparam (#3164)
- [pre-commit.ci] pre-commit autoupdate (#3163)

Version 0.160.1 (Released September 23, 2024)
---------------

- revert: revert the pygsheet uprgade https://github.com/mitodl/mitxpro/pull/2736 (#3161)
- fix(deps): update python to v3.12.6 (#3151)

Version 0.160.0 (Released September 23, 2024)
---------------

- feat: add sorting option (#3129)
- fix: support email address from configurations(settings) on all templates (#3157)
- feat: load topics in bulk from CSV (#3156)
- fix(deps): update dependency user-util to v0.3.1

Version 0.159.1 (Released September 19, 2024)
---------------

- fix(deps): update dependency boto3 to v1.35.21
- [pre-commit.ci] pre-commit autoupdate (#3152)
- fix(deps): update dependency boto3 to v1.35.19
- chore(deps): update dependency factory-boy to v3.3.1
- Don't fail app init if settings.py is reloaded
- fix: don't generate report.html file for RC and Production (#3125)
- fix(deps): update dependency express to v4.20.0 [security] (#3147)
- chore(deps): update dependency pytest to v8 (#3141)
- fix(deps): update dependency yup to v1 (#3061)
- fix(deps): update dependency mocha to v10 (#3144)
- chore(deps): update postgres docker tag to v16 (#3138)
- Revert "fix(deps): update dependency sass to ~1.78.0" (#3145)
- [pre-commit.ci] pre-commit autoupdate (#3142)
- fix(deps): update dependency pycountry to v24 (#3139)
- fix(deps): update dependency webpack-bundle-tracker to v1.8.1 (#3136)
- fix(deps): update dependency google-api-python-client to v2.144.0
- fix(deps): update dependency django to v4.2.16
- fix(deps): update dependency boto3 to v1.35.14
- fix: use support email address from configurations(settings) (#3127)
- fix(deps): update dependency sass to ~1.78.0
- [pre-commit.ci] pre-commit autoupdate (#3126)
- chore(deps): update dependency ruff to ^0.6.0 (#3115)

Version 0.159.0 (Released September 09, 2024)
---------------

- fix(deps): update dependency css-loader to v7 (#3086)
- fix(deps): update dependency google-auth to v2.34.0
- fix(deps): update dependency google-api-python-client to v2.143.0
- fix(deps): update dependency django-robots to v6.1
- fix(deps): update dependency django-hijack to v3.6.0
- fix(deps): update dependency boto3 to v1.35.8
- chore(deps): update postgres docker tag to v15.8 (#3117)
- chore(deps): update node.js to v20.17.0 (#3116)
- chore(deps): update nginx docker tag to v1.27.1 (#3114)
- fix(deps): update python to v3.12.5 (#3003)
- chore(deps): lock file maintenance (#3113)
- feat: display tax details for countries where taxes are enabled (#3109)
- fix(deps): update dependency zeep to v4 (#3062)
- fix(deps): update dependency pygsheets to v2.0.6 (#2736)
- fix(deps): update dependency webpack to v5.94.0 [security]
- Python upgrade from 3.9.x to 3.12.x (#3089)

Version 0.158.0 (Released August 29, 2024)
---------------

- [pre-commit.ci] pre-commit autoupdate (#3110)
- Upgrade Webpack from v4 to v5 (#3091)
- perf: improve API performance (#3106)
- feat: add hybrid format option for courseware page (#3105)
- fix: silently fail name validation on connection error (#3107)

Version 0.157.1 (Released August 22, 2024)
---------------

- [pre-commit.ci] pre-commit autoupdate (#3104)
- fix: prevent HTML/URLs in the Full Name field (#2994)

Version 0.157.0 (Released August 19, 2024)
---------------

- fix: fixed basket deletion issue (#3102)
- [pre-commit.ci] pre-commit autoupdate (#3100)
- feat: added a celery task to delete expired basket (#3021)

Version 0.156.2 (Released August 13, 2024)
---------------

- feat: add course and program availability in APIs (#3098)

Version 0.156.1 (Released August 08, 2024)
---------------

- Revert "feat: add course and program availability in APIs (#3094)" (#3096)
- feat: add course and program availability in APIs (#3094)
- test(emeritus_api): add more tests for emeritus API ingestion (#3032)
- chore: upgrade node to v20 (#3090)
- fix(deps): update dependency django to v4.2.15 [security]
- [pre-commit.ci] pre-commit autoupdate (#3088)

Version 0.156.0 (Released August 06, 2024)
---------------

- feat(emeritus course sync): add image and certificates for external courses (#3064)
- fix: catalog external courses page visibility conditions (#3082)
- chore(deps): lock file maintenance
- temp: remove package manager from package.json (#3084)

Version 0.155.0 (Released August 02, 2024)
---------------

- feat: set enrollment end for emeritus courses (#3073)
- feat: optimize catalog queries for external coursware (#3071)
- revert: yarn downgrade and adding it to engine (#3081)
- chore: downgrade yarn to 3.1.0 (#3078)
- chore: add yarn to engines (#3077)
- test: fix flaky test (#3074)
- fix: do not publish external course if saved as draft (#3072)
- fix: catalog prices for external courses (#3070)
- [pre-commit.ci] pre-commit autoupdate (#3068)
- fix: version for django-robots (#3069)
- fix(external course sync): publish revision if course is live and has unpublished changes (#3065)
- fix: add productversion description for CMS products and raise error if empty (#3041)
- chore(deps): update yarn to v3.8.3 (#2860)
- fix(deps): update dependency pillow to v10.4.0
- fix(deps): update dependency django-storages to v1.14.4
- fix(deps): update dependency boto3 to v1.34.149
- fix: draft page issues in API ingestion (#3048)
- chore: switch migrations to the release phase (#3054)

Version 0.154.0 (Released July 24, 2024)
---------------

- fix(deps): update dependency sass to v1.77.6 (#3015)
- fix(deps): update dependency sentry-sdk to v2 (#3055)
- [pre-commit.ci] pre-commit autoupdate (#3053)
- feat: added task id logs for sync_db_to_hubspot command (#3040)

Version 0.153.2 (Released July 22, 2024)
---------------

- fix(deps): update dependency ramda to ^0.30.0 (#3013) (#3047)
- chore(deps): update dependency ruff to ^0.5.0
- [pre-commit.ci] pre-commit autoupdate (#3033)
- fix: process_coupon_assignment_sheet warnings and errors (#3034)

Version 0.153.1 (Released July 15, 2024)
---------------

- feat: add products and product versions for emeritus products (#3045)
- Revert "fix(deps): update dependency ramda to ^0.30.0 (#3013)" (#3044)
- fix(deps): update dependency ramda to ^0.30.0 (#3013)

Version 0.153.0 (Released July 15, 2024)
---------------

- feat: welcome emails for xPRO Learners  (#3017)
- fix(deps): update dependency wagtail to v5.2.6 [security]
- fix: homepage watch now video (#3039)
- fix(deps): update dependency django to v4.2.14 [security]

Version 0.152.0 (Released July 09, 2024)
---------------

- feat: replace # with - in Emeritus courserun.courseware_id (#3035)
- fix: remove spaces from the product version text_id fields (#3023)
- chore: add fake EMERITUS_API_KEY to .env.example (#3030)
- [pre-commit.ci] pre-commit autoupdate (#3025)
- fix(deps): update dependency djangorestframework to v3.15.2 [security]

Version 0.151.0 (Released July 02, 2024)
---------------

- fix(external course sync): sync course run dates if they are missing (#3027)
- feat: ingest external course APIs (#2998)

Version 0.150.0 (Released June 24, 2024)
---------------

- [pre-commit.ci] pre-commit autoupdate (#3022)
- Add -E flag to worker subcommand for sending task events
- Revert "Add flag for Celery to send task state change events"
- docs: replaced mitxpro-openedx-extensions with openedx-companion-auth in readme (#3020)
- Add flag for Celery to send task state change events

Version 0.149.1 (Released June 12, 2024)
---------------

- revert: downgrade django-hijack from 3.5.1 to 3.4.5 (#3018)
- [pre-commit.ci] pre-commit autoupdate (#3001)
- feat: add external course id fields and enhance admin models (#3006)
- refactor: upgrade docker-compose & CI postgres version to 15 (#3004)
- fix(deps): update dependency redis to v4.6.0
- fix(deps): update dependency pynacl to v1.5.0
- fix(deps): update dependency psycopg2 to v2.9.9
- fix(deps): update dependency django-hijack to v3.5.1
- chore(deps): update nginx docker tag to v1.27.0
- fix(deps): update dependency uwsgi to v2.0.26
- fix(deps): update dependency boto3 to v1.34.122
- fix(deps): update dependency pycountry to v19.8.18
- fix(deps): update dependency mini-css-extract-plugin to ^0.12.0 (#2993)
- fix(deps): update dependency hls.js to ^0.14.0 (#2992)
- fix(deps): update dependency eslint-config-google to ^0.14.0 (#2975)
- [pre-commit.ci] pre-commit autoupdate (#2997)

Version 0.149.0 (Released June 10, 2024)
---------------

- fix: sync start dates for programs & courses between Program/Course pages & APIs (#2999)

Version 0.148.0 (Released May 30, 2024)
---------------

- fix: invalid certificate uuid should raise 404 (#2990)
- chore(deps): bump @babel/traverse from 7.16.3 to 7.24.6 (#2995)
- fix(deps): update dependency boto3 to v1.34.113
- refactor: remove EdX-Api-Key usage (#2982)
- fix(deps): update dependency google-api-python-client to v1.12.11 (#2987)
- fix(deps): update dependency google-auth to v1.35.0

Version 0.147.0 (Released May 22, 2024)
---------------

- fix: intermittent/flaky test assertion failure in test_sync_courseruns_data (#2983)
- chore(deps): update postgres docker tag to v12.19
- fix(deps): update dependency django to v4.2.13
- fix(deps): update dependency boto3 to v1.34.108
- [pre-commit.ci] pre-commit autoupdate (#2981)
- chore(deps): bump get-func-name from 2.0.0 to 2.0.2 (#2770)
- chore(deps): update akhileshns/heroku-deploy digest to 581dd28 (#2719)

Version 0.146.2 (Released May 14, 2024)
---------------

- refactor: remove ENABLE_ORDER_RECEIPTS (#2964)
- [pre-commit.ci] auto fixes from pre-commit.com hooks
- Pre commit linting (#2955)
- fix(deps): update dependency django-storages to v1.14.3
- fix(deps): update dependency flaky to v3.8.1
- fix(deps): update dependency celery to v5.4.0
- fix(deps): update dependency edx-api-client to v1.8.0
- fix(deps): update dependency wagtail to v5.2.5
- fix(deps): update dependency boto3 to v1.34.98

Version 0.146.1 (Released May 06, 2024)
---------------

- fix: check for courseware object in cms (#2968)
- chore(deps): update dependency ruff to ^0.4.0 (#2962)
- chore(deps): update nginx docker tag to v1.26.0
- fix(deps): update dependency boto3 to v1.34.96

Version 0.146.0 (Released May 02, 2024)
---------------

- fix: fix codecov workflow version (#2966)
- feat: hide extra course runs in checkout if voucher is applied (#2960)
- fix(deps): update dependency uwsgi to v2.0.25.1 (#2958)
- fix(deps): update dependency boto3 to v1.34.88 (#2957)
- chore(deps): update nginx docker tag to v1.25.5 (#2956)
- chore(deps-dev): bump cryptography from 41.0.5 to 42.0.4 (#2903)
- feat!: remove partial voucher matching (#2940)
- Fix: This commit adds two Celery configurables

Version 0.145.1 (Released April 18, 2024)
---------------

- Enable fields for coupon and b2bcoupon to be editable (#2951)
- chore(deps): bump express from 4.18.2 to 4.19.2 (#2926)
- fix(deps): update dependency pillow to v10 [security] (#2748)
- fix(deps): update dependency drf-flex-fields to v0.9.9
- chore(deps): update dependency astroid to v2.15.8

Version 0.145.0 (Released April 16, 2024)
---------------

- feat: add ruff (#2865)
- fix(deps): update dependency djangorestframework to v3.15.1
- fix(deps): update dependency django-storages to v1.14.2
- fix(deps): update dependency wagtail to v5.2.4
- fix(deps): update dependency boto3 to v1.34.84
- chore(deps): bump browserify-sign from 4.2.1 to 4.2.3 (#2944)

Version 0.144.0 (Released April 09, 2024)
---------------

- feat: change courseware pricing in CMS (#2828)
- chore(deps): bump webpack-dev-middleware from 3.7.3 to 5.3.4 (#2921)

Version 0.143.0 (Released April 05, 2024)
---------------

- Styling for the hubspot forms fields available in the list provided (#2939)
- chore(deps): bump ip from 1.1.5 to 1.1.9 (#2902)
- chore(deps-dev): bump jwcrypto from 1.5.4 to 1.5.6 (#2916)
- chore(deps): bump es5-ext from 0.10.53 to 0.10.64 (#2918)
- fix: ignore git guardian secret on local docker compsoe (#2938)

Version 0.142.0 (Released April 02, 2024)
---------------

- Don't allow duplicate coupon codes (#2888)
- fix(deps): update dependency django-oauth-toolkit to v1.7.1
- fix(deps): update dependency django-anymail to v8.6
- chore(deps): update postgres docker tag to v12.18
- chore(deps): update dependency safety to v3.1.0
- chore(deps): update dependency pytest-mock to v3.14.0
- fix(deps): update dependency wagtail to v5.2.3
- fix(deps): update dependency uwsgi to v2.0.24
- fix(deps): update dependency boto3 to v1.34.74
- chore: set time fields for start/end date in Django with a default time (#2912)
- style: replace PNG logo high quality (#2927)

Version 0.141.0 (Released March 28, 2024)
---------------

- feat: Add "sign up for more information" on the xPRO product pages (#2906)
- fix: use raw id for voucher admin to avoid timeout (#2917)
- feat: remove legacy zendesk snippets (#2913)
- chore(deps): update nginx docker tag to v1.25.4
- Update the tax calculation rules to charge more aggressively (#2914)
- fix(deps): update dependency django to v4.2.11 [security]

Version 0.140.0 (Released March 26, 2024)
---------------

- chore: Upgrade Django to 4.2 (#2867)
- fix(deps): update dependency mitol-django-mail to v2023.12.19
- fix(deps): update dependency mitol-django-hubspot-api to v2023.12.19
- fix(deps): update dependency mitol-django-common to v2023.12.19
- fix(deps): update dependency mitol-django-digital-credentials to v2023.12.19

Version 0.139.0 (Released February 13, 2024)
---------------

- style: fix email logo (#2893)
- style: add favicon and fix certificate partner logo design (#2891)
- fix(deps): update dependency django to v3.2.24 [security]
- style: update logo (#2881)

Version 0.138.2 (Released February 02, 2024)
---------------

- feat: add prod zd-site-verification and hard code it (#2883)

Version 0.138.1 (Released January 31, 2024)
---------------

- fix: make vat_id blank only to fix profile update(#2880)
- Delete more obsolete github templates (#2875)

Version 0.138.0 (Released January 25, 2024)
---------------

- fix: fix static image path for enterprise page (#2878)
- fix: hide child page urls in sitemap (#2876)
- feat: add enterprise page link in header (#2871)
- feat: add sitemap (#2870)
- feat: enterprise page (#2834)
- Delete .github/PULL_REQUEST_TEMPLATE directory

Version 0.137.1 (Released January 16, 2024)
---------------

- feat: add zd-site-verification tag (#2864)
- test: improve test fixture (#2863)
- fix(deps): update dependency boto3 to v1.34.14
- chore(deps): update dependency responses to v0.24.1
- chore(deps): update dependency pytest-django to v4.7.0
- fix(deps): update dependency uwsgi to v2.0.23
- fix(deps): update dependency wagtail to v5.2.2
- chore(deps): update dependency pytest-env to v1.1.3
- chore(deps): update dependency pytest to v7.4.4
- fix: Add vat id in hubspot properties sync (#2851)

Version 0.137.0 (Released January 16, 2024)
---------------

- fix: filter revision created by wagtail (#2849)
- fix: Add content_type to revision.content for blog and webinar index pages (#2846)
- chore(deps): update dependency pylint-django to v2.5.5
- chore!: Upgrade wagtail to 5.x (#2830)

Version 0.136.0 (Released January 02, 2024)
---------------

- feat: add vat number (#2764)

Version 0.135.2 (Released December 20, 2023)
---------------

- style: Order receipt design tweaks (#2833)
- fix: return topics with more than zero courses (#2839)

Version 0.135.1 (Released November 30, 2023)
---------------

- feat: enable header links and disable new and events on homepage (#2836)

Version 0.135.0 (Released November 27, 2023)
---------------

- feat: xPro blog (#2789)
- refactor: local seed command to support platforms (#2825)

Version 0.134.0 (Released November 07, 2023)
---------------

- fix: postgres startup error without password (#2822)
- fix(deps): update dependency django to v3.2.23 [security]
- fix: Unify decimal places for price and discount (#2821)
- style: design tweaks in webinar designs (#2820)
- fix(deps): update dependency babel-loader to v8.3.0
- fix(deps): update babel monorepo
- chore(deps): update yarn to v3.6.4
- chore(deps): update postgres docker tag to v11.16
- chore(deps): update nginx docker tag to v1.25.3
- chore(deps): update docker.elastic.co/elasticsearch/elasticsearch docker tag to v6.8.23
- chore(deps): update dependency safety to v2.3.5

Version 0.133.0 (Released November 02, 2023)
---------------

- fix(deps): update dependency pytest and mitol-django-* (#2809)
- feat: add xpro catalog link when no courseware is associated (#2801)
- chore(deps): update dependency pytest-mock to v3.12.0 (#2803)
- fix(deps): update dependency django to v3.2.22 (#2802)

Version 0.132.2 (Released October 23, 2023)
---------------

- fix: receipt email typo (#2799)
- fix: display discount amount as negative (#2794)

Version 0.132.1 (Released October 18, 2023)
---------------

- fix: configure course or program format (#2747)

Version 0.132.0 (Released October 16, 2023)
---------------

- fix: platform name search in Django Admin Courses/Programs (#2792)
- feat: display tax rate on checkout, receipt and email (#2790)
- fix: make `platform` a required field for Courses/Programs (#2786)
- fix(deps): update dependency ipython to v8.16.1

Version 0.131.0 (Released October 03, 2023)
---------------

- feat: Add feat flag for taxes display (#2783)
- Adds indexes to the netblock table (#2780)
- tests: adds frontend tests for the taxes (#2779)
- Fixing formatting errors on receipt page, should not charge tax if TaxRate (#2775)
- fix(deps): update dependency chai to v4.3.10
- feat: display tax in regular checkout (#2773)
- chore(deps): lock file maintenance
- Adds tax rate calculation support (#2772)
- feat: force all enrollments (#2763)

Version 0.130.0 (Released September 26, 2023)
---------------

- chore(deps): update dependency faker to v13.16.0
- chore(deps): update dependency factory-boy to v3.3.0
- chore(deps): update dependency black to v22.12.0
- fix(deps): update dependency webpack-hot-middleware to v2.25.4
- fix(deps): update dependency unzipper to v0.10.14
- fix(deps): update dependency shelljs to v0.8.5
- fix(deps): update dependency reselect to v4.1.8
- fix(deps): update dependency redux-asserts to ^0.0.12
- chore(deps): update dependency freezegun to v0.3.15
- feat: Use poetry instead of requirements files (#2715)

Version 0.129.0 (Released September 13, 2023)
---------------

- fix: update hubspot settings default values (#2724)
- fix(deps): update dependency react-hot-loader to v4.13.1
- fix(deps): update dependency object.entries to v1.1.7
- fix(deps): update dependency enzyme-adapter-react-16 to v1.15.7
- fix(deps): update dependency chai to v4.3.8
- fix(deps): update dependency bootstrap to v4.6.2
- chore(deps): update dependency wcwidth to v0.2.6
- chore(deps): update dependency uwsgi to v2.0.22
- chore(deps): update dependency s3transfer to v0.6.2
- chore(deps): update dependency urllib3 to v1.26.16
- chore(deps): update dependency prompt-toolkit to v3.0.39
- chore(deps): update dependency minimist to v1.2.8
- chore(deps): update dependency matplotlib-inline to v0.1.6
- chore(deps): update dependency markupsafe to v2.1.3
- chore(deps): update dependency lxml to v4.9.3
- chore(deps): update dependency django-silk to v5.0.3
- chore(deps): update dependency django to v3.2.21
- chore(deps): update dependency django-ipware to v3.0.7
- chore(deps): update dependency autopep8 to v2.0.4
- chore(deps): update dependency cffi to v1.15.1

Version 0.128.0 (Released September 07, 2023)
---------------

- refactor!: rename visible_in_bulk_form to is_private in product model (#2716)
- chore(deps): update dependency async-timeout to v4.0.3
- chore(deps): update dependency anyascii to v0.3.2

Version 0.127.1 (Released August 31, 2023)
---------------

- feat: Add platform model and associated fields in Course and Program models (#2699)
- chore(deps): bump cryptography from 40.0.2 to 41.0.3 (#2693)
- chore(deps): bump certifi from 2022.12.7 to 2023.7.22 (#2692)
- chore(deps): bump tough-cookie from 4.0.0 to 4.1.3 (#2684)

Version 0.127.0 (Released August 29, 2023)
---------------

- fix: include todays webinars in upcoming webinars list (#2713)
- feat: add ondemand webinar body text field (#2704)
- Add renovate.json (#2680)

Version 0.126.0 (Released August 23, 2023)
---------------

- fix: certificate revision validation in Django Admin Certificate model (#2701)
- fix: more dates links for external courseware (#2696)

Version 0.125.0 (Released August 16, 2023)
---------------

- feat: Added webinars detail page (#2690)
- feat: update catalog ordering (#2694)
- chore(deps): bump qs from 6.10.1 to 6.11.0 (#2688)
- chore(deps): bump pygments from 2.11.2 to 2.15.0 (#2691)
- Force enrollment when deferring enrollment (#2685)
- chore(deps): bump word-wrap from 1.2.3 to 1.2.4 (#2689)
- chore(deps): bump django from 3.2.19 to 3.2.20 (#2683)
- Seed Data updated, data validation added in seed command (#2673)
- fix: course not found errros on sentry (#2681)

Version 0.124.3 (Released July 17, 2023)
---------------

- refactor: Minor code changes
- style: linting issues resolved
- fix: Added new message
- test: Added new tests and updated existing ones
- refactor: Added code changes
- style: unused import removed
- fix: fixed broken test
- fix: added tests and fixed broken tests
- style: liniting
- fix: Certificate generation via course enrollments
- Review changes
- Code refactored
- :sparkles: Black formatted
- Tests added for the management command
- Code refactored, error messages improved
- Manage program Certificates Command
- Certificates creation does not halt entire process
- Bump express from 4.17.1 to 4.17.3
- Bump ipython from 7.32.0 to 8.10.0

Version 0.124.2 (Released June 22, 2023)
---------------

- Fixing stuff from comments
- fix: Unintended leak of Proxy-Authorization header in requests (#2670)
- fix: bump certifi from 2021.10.8 to 2022.12.7 (#2669)
- ran black
- Adding command to invalidate coupons

Version 0.124.1 (Released June 06, 2023)
---------------

- fix: create enrollments when token creation fails (#2656)
- Bump sqlparse from 0.4.2 to 0.4.4 (#2632)
- fix: dependabot security alert regarding django validation (#2664)

Version 0.124.0 (Released June 05, 2023)
---------------

- feat: add feat flag for courses dropdown & webinars (#2666)
- Manually bump cryptography from 38.0.3 to 40.0.2 (#2654)
- Do not log an error if HUBSPOT_CREATE_USER_FORM_ID is unset; sync hubspot contact on login (#2662)
- Use new hubspot_api version and try to sync contacts individually if a batched sync chunk fails (#2653)
- chore: remove course/course topic association (#2649)
- hotfix: hide the Webinars link from top app bar (#2658)
- feat: catalog topics dropdown (#2635)
- Bump oauthlib from 3.2.0 to 3.2.2 (#2564)
- Bump http-cache-semantics from 4.1.0 to 4.1.1 (#2562)
- feat: Update management command for user deferrals to include courses with closed enrollments (#2646)
- fix: Two accounts with the same email (#2642)

Version 0.123.1 (Released May 25, 2023)
---------------

- hotfix: hide the Webinars link from top app bar (#2658)

Version 0.123.0 (Released May 24, 2023)
---------------

- feat: webinars (#2624)

Version 0.122.0 (Released May 18, 2023)
---------------

- Bump terser from 4.8.0 to 4.8.1 (#2459)
- Bump moment from 2.29.1 to 2.29.4 (#2460)
- chore: bump sentry version to 1.22.0 (#2641)
- chore: remove external_marketing_url from course and program run (#2639)

Version 0.121.3 (Released May 09, 2023)
---------------

- fix: checkout when there is a course without course page (#2644)
- fix: Bad B2BOrder email values cause exceptions when syncing to Hubspot (#2626)

Version 0.121.2 (Released May 09, 2023)
---------------

- chore: external courseware unused fields cleanup (#2587)

Version 0.121.1 (Released May 04, 2023)
---------------

- Bump redis from 3.5.3 to 4.4.4 (#2605)

Version 0.121.0 (Released May 03, 2023)
---------------

- feat: order topics alphabetically on HomePage and CatalogPage (#2634)
- fix: Error creating Open edX user. user already exists or invalid name (follow-up) (#2592)
- feat: mimic Learn more feat for Internal courseware as well (#2628)

Version 0.120.0 (Released April 20, 2023)
---------------

- fix: make the course topics selection optional in CMS (#2627)
- fix: fix topic height when line length increases (#2625)
- feat: update APIs to support external courseware data and additional API fields (#2608)
- fix: update the migrations to handle external course topics as well (#2622)
- feat: view courses by topic (#2609)
- fix: Only link courses in programs that have live CMS page (#2620)
- fix: Sheets deferral failed but no error was recorded in sheet (#2610)

Version 0.119.2 (Released April 12, 2023)
---------------

- fix: remove codecov package due to its PyPI distribution issue (#2618)

Version 0.119.1 (Released April 12, 2023)
---------------

- fix: data collision issue with existing external courseware Readable Ids (#2612)
- fix: do not display courses with closed enrollment in boeing voucher upload (#2603)
- fix: Cannot create ProductCouponAssignments for codes that have already been redeemed error message to info message (#2607)

Version 0.119.0 (Released April 05, 2023)
---------------

- fix: don't allow external products to be sellable (#2602)
- fix: UserCreationFailedException (#2588)
- fix: external program URL on Program Details/Product page (#2599)
- feat: associate external courseware with Django models (#2585)
- fix: Error creating Open edX user. user already exists or invalid name (#2579)

Version 0.118.0 (Released March 07, 2023)
---------------

- Bump django from 3.2.17 to 3.2.18 (#2576)
- fix: certificates jobs should continue on errors rather than halting (#2580)

Version 0.117.0 (Released February 23, 2023)
---------------

- Limit full name length to 255 characters (#2578)

Version 0.116.1 (Released February 16, 2023)
---------------

- Check if edx enrollment already exists for failed enrollments (#2559)

Version 0.116.0 (Released February 13, 2023)
---------------

- Prevent promo code from applying to products that require enrollment code
- Create a new auth token if the old one fails to work/refresh (#2473)

Version 0.115.0 (Released February 13, 2023)
---------------

- Fix processing of scheduled sheet coupon assignment tasks (#2565)
- Bump pyjwt from 2.3.0 to 2.4.0 (#2397)
- Bump minimist from 1.2.5 to 1.2.6 (#2382)
- Bump loader-utils from 1.4.0 to 1.4.2 (#2466)
- Bump ua-parser-js from 0.7.31 to 0.7.33 (#2552)
- Bump django from 3.2.15 to 3.2.17 (#2563)
- Fix flaky test (#2557)
- Add frontend caching for homepage (#2529)
- Add a workflow for new issues
- Change ubuntu-latest to ubuntu-22.04 (#2554)

Version 0.114.1 (Released January 30, 2023)
---------------

- Fix bug with calling b2b deal sync function from helper task (#2551)

Version 0.114.0 (Released January 26, 2023)
---------------

- Revert "Force django app to load ASAP after uwsgi workers are restarted/forked (#2527)" (#2548)
- Only return courses/programs with live cms pages in the catalog API response (#2545)
- Bump cookiejar from 2.1.3 to 2.1.4 (#2544)
- Course urls in catalog API (#2540)
- Bump decode-uri-component from 0.2.0 to 0.2.2 (#2506)
- Update README.md
- single_task and raise_429 decorators for hubspot tasks (#2537)
- Bump json5 from 1.0.1 to 1.0.2 (#2536)
- Hubspot batch sync improvements (#2535)
- fix: 404 page doesn't need authentication (#2534)
- perf: Optimize database queries (#2525)
- Force django app to load ASAP after uwsgi workers are restarted/forked (#2527)

Version 0.113.0 (Released January 25, 2023)
---------------

- fix: Catalog page performance (#2532)
- Setup django-silk when DEBUG=True
- Adds a separate step for black formatting check (#2528)
- Remove bulk enrollment form (#2482)
- Remove uwsgi worker reload settings

Version 0.112.6 (Released December 09, 2022)
---------------

- fix: enhance home page queries wagtail (#2501)
- Improve unused coupon query (#2509)
- Refactor condition
- Fix tests
- Rename property
- Use cached_property
- fmt
- Reduce queries for Product pages

Version 0.112.5 (Released December 07, 2022)
---------------

- upgrade newrelic (#2511)

Version 0.112.4 (Released December 05, 2022)
---------------

- Fixed index on ProductCouponAssignment

Version 0.112.3 (Released December 01, 2022)
---------------

- Updated nginx to drop wagtail images Vary header

Version 0.112.2 (Released December 01, 2022)
---------------

- Remove commented breakpoint
- Fix course page ordering
- Fix prefetch
- Optimize properties
- Prefetch program products
- Add default for next
- Optimized some queries
- Revert API changes
- Add imports
- Revert changes in serializers
- Improve Backend Performance

Version 0.112.1 (Released November 30, 2022)
---------------

- Bump django-storages and boto3

Version 0.112.0 (Released November 29, 2022)
---------------

- Upgrade cryptography, remove django-server-status (#2483)

Version 0.111.1 (Released November 22, 2022)
---------------

- Upgrade uwsgi

Version 0.111.0 (Released November 22, 2022)
---------------

- feat: Add support for dollars-off coupons (#2475)
- Update openedx setup doc (#2474)
- Fixed improper usages of get_rendition

Version 0.110.0 (Released November 21, 2022)
---------------

- Upgrade sentry sdk
- bulk assignment instance already created (#2461)
- Replace Ecommerce Bridge API with CRM API for hubspot syncing (#2437)

Version 0.109.0 (Released November 14, 2022)
---------------

- Process coupon requests if spreadsheet got updated (#2426)

Version 0.108.2 (Released November 02, 2022)
---------------

- revert: certificate revisions prior to August 8 2022 (#2440)
- Update canius-lite (#2442)

Version 0.108.1 (Released October 31, 2022)
---------------

- Bump lxml from 4.8.0 to 4.9.1 (#2401)

Version 0.108.0 (Released October 27, 2022)
---------------

- chore: add support for Heroku-22 stack (#2430)
- add webpack bundle analyzer

Version 0.107.3 (Released September 21, 2022)
---------------

- Bump django from 3.2.14 to 3.2.15 (#2405)

Version 0.107.2 (Released September 20, 2022)
---------------

- Versioning of certificate template (#2416)
- xPro-2411 Fix search for data consent agreements admin
- certificate page should not be moved from course child to certificate index child (#2422)

Version 0.107.1 (Released September 15, 2022)
---------------

- display start and end date on certificate template (#2421)

Version 0.107.0 (Released September 15, 2022)
---------------

- centered css for certificate (#2418)

Version 0.106.0 (Released August 31, 2022)
---------------

- Partner logo in certificate template (#2407)

Version 0.105.0 (Released July 07, 2022)
---------------

- Bump django from 3.2.12 to 3.2.14 (#2399)

Version 0.104.0 (Released June 27, 2022)
---------------

- Integrate the cache control max_age jitter decorator form mitol-django-common (#2390)

Version 0.103.0 (Released May 24, 2022)
---------------

- Update canius-lite (#2395)

Version 0.102.5 (Released May 16, 2022)
---------------

- Added heroku deployment workflows

Version 0.102.4 (Released April 11, 2022)
---------------

- Add option to require enrollment code at checkout for specified products (#2380)

Version 0.102.3 (Released April 07, 2022)
---------------

- Bump django from 3.2.5 to 3.2.12 (#2359)
- Added unittest for expired program runs (#2379)

Version 0.102.2 (Released March 30, 2022)
---------------

- Updated the query to filter correct data (#2376)

Version 0.102.1 (Released March 23, 2022)
---------------

- Fixed password reset url

Version 0.102.0 (Released March 21, 2022)
---------------

- set the react version to get rid of a lint warning

Version 0.101.0 (Released March 21, 2022)
---------------

- Split the queries to evaluate (#2368)
- Digital Credentials: UI Changes for DCC integration (#2364)
- Upgrade django-storage (#2363)
- asadiqbal08/ Django Version bump (#2343)
- chore: remove unused dependency (validator) (#2357)

Version 0.100.1 (Released March 07, 2022)
---------------

- bundle optimization in webpack (#2350)
- remove Sanctuary library

Version 0.100.0 (Released February 23, 2022)
---------------

- Bump celery, redis and celery-redbeat (#2340)

Version 0.99.0 (Released February 08, 2022)
--------------

- Bump django from 2.2.25 to 2.2.26 (#2346)
- Bump django-filter from 2.3.0 to 2.4.0 (#2345)

Version 0.98.2 (Released January 31, 2022)
--------------

- Bump ipython from 7.17.0 to 7.31.1 (#2344)

Version 0.98.1 (Released January 03, 2022)
--------------

- Bump django from 2.2.24 to 2.2.25 (#2334)

Version 0.98.0 (Released December 21, 2021)
--------------

- Bump lxml from 4.6.3 to 4.6.5 (#2329)

Version 0.97.1 (Released December 14, 2021)
--------------

- updated compose file
- fixed formatting issue
- added ol-django-authentication app to MITxPro

Version 0.97.0 (Released November 30, 2021)
--------------

- added --exit option to mocha
- addressed feedback
- updated react-picky version and fixed import
- updated yarn to 3.1

Version 0.96.0 (Released October 05, 2021)
--------------

- removed unsued dependency
- Bump tar from 4.4.10 to 4.4.19

Version 0.95.1 (Released September 30, 2021)
--------------

- Bump pillow from 8.2.0 to 8.3.2 (#2305)
- Bump path-parse from 1.0.6 to 1.0.7 (#2301)

Version 0.95.0 (Released September 21, 2021)
--------------

- Updated styles for news and event carousel

Version 0.94.0 (Released August 10, 2021)
--------------

- upgrading deep-extend to 0.6.0 (#2295)

Version 0.93.1 (Released July 29, 2021)
--------------

- fix: fetch correct customer name on the b2b reciepts (#2293)

Version 0.93.0 (Released July 27, 2021)
--------------

- upgrade glob-parent to 5.1.2 (#2292)

Version 0.92.0 (Released July 26, 2021)
--------------

- update mocha for diff dependecny upgrade (#2290)

Version 0.91.3 (Released July 19, 2021)
--------------

- asadiqbal08/News and Events carousel to product pages (#2279)

Version 0.91.2 (Released July 14, 2021)
--------------

- marked flaky for a test (#2274)

Version 0.91.1 (Released July 08, 2021)
--------------

- migrate from node-sass to sass (#2273)

Version 0.91.0 (Released July 07, 2021)
--------------

- Bump wagtail from 2.12.4 to 2.12.5 (#2266)

Version 0.90.1 (Released June 28, 2021)
--------------

- upgrade trim-newlines to v3.0.1 (#2270)

Version 0.90.0 (Released June 23, 2021)
--------------

- asadiqbal08/The customer support link should be underlined (#2267)
- fix: validation for duplicate contract_number in order creation (#2259)

Version 0.89.2 (Released June 17, 2021)
--------------

- asadiqbal08/Update block_users on email address that wasn't already registered. (#2262)
- asadiqbal08/command unblock_users to remove users from the blocklist. (#2254)
- asadiqbal08/Standalone block user command and code refactoring (#2257)

Version 0.89.1 (Released June 14, 2021)
--------------

- Bump yargs-parser from 13.1.1 to 13.1.2 (#2250)
- Bump lodash-es from 4.17.11 to 4.17.21 (#2253)
- Bump ua-parser-js from 0.7.19 to 0.7.28 (#2251)
- Bump eslint-utils from 1.3.1 to 1.4.3 (#2252)
- Bump django from 2.2.21 to 2.2.24 (#2255)
- build: bump react-markdown for transitive trim dependency alert (#2237)

Version 0.89.0 (Released June 11, 2021)
--------------

- fix: don't fail CI on coverage (#2245)
- Bump normalize-url from 4.5.0 to 4.5.1 (#2244)
- build: upgrade boto3, sentry-sdk and requests to fix urllib3 alert (#2241)
- Blocklist: Check for blocked emails when registering users (#2239)
- Bump django from 2.2.20 to 2.2.21 (#2242)

Version 0.88.1 (Released June 09, 2021)
--------------

- asadiqbal08/Add -blocklist option to retire_users command (#2230)
- Bump browserslist from 4.6.6 to 4.16.6 (#2228)

Version 0.88.0 (Released June 02, 2021)
--------------

- Update digital-credentials dependency
- Bump ws from 7.2.3 to 7.4.6 (#2232)

Version 0.87.1 (Released May 27, 2021)
--------------

- Yup version bump (#2223)

Version 0.87.0 (Released May 25, 2021)
--------------

- upgrade merge version (#2224)
- Defer youtube rendering script (#2179)

Version 0.86.3 (Released May 21, 2021)
--------------

- Add support for Global Data Consent Agreement (#2201)
- Bump hosted-git-info from 2.8.4 to 2.8.9 (#2204)
- Removing unsed handlebars package (#2212)
- Bump lodash from 4.17.19 to 4.17.21 (#2203)
- Removed reference to Professional Track (#2221)

Version 0.86.2 (Released May 20, 2021)
--------------

- update refund policy link in checkout page (#2217)

Version 0.86.1 (Released May 12, 2021)
--------------

- Format code
- update PR template
- fix contexts

Version 0.86.0 (Released May 10, 2021)
--------------

- Fix github actions by updating apt dependency list (#2206)

Version 0.85.1 (Released May 10, 2021)
--------------

- Bump Pillow to 8.2.0 & wagtail to 2.12.4 (#2156)

Version 0.85.0 (Released May 04, 2021)
--------------

- Bump rsa from 4.1 to 4.7 (#2199)
- Bump urllib3 from 1.25.3 to 1.25.8 (#2198)

Version 0.84.2 (Released April 27, 2021)
--------------

- Upgrade djangorestframework to 3.12.4, djoser to 2.1.0 and social-auth-app-django to 4.0.0 (#2193)

Version 0.84.1 (Released April 22, 2021)
--------------

- changing text in program certificates (#2189)

Version 0.84.0 (Released April 21, 2021)
--------------

- Bump ssri from 6.0.1 to 6.0.2 (#2191)

Version 0.83.2 (Released April 20, 2021)
--------------

- Bump django from 2.2.18 to 2.2.20 (#2183)

Version 0.83.1 (Released April 16, 2021)
--------------

- Showing receipt Link in case of individual courses run purchases of a program (#2175)
- Bump lxml from 4.6.2 to 4.6.3 (#2164)

Version 0.83.0 (Released April 13, 2021)
--------------

- asadiqbal08/Remove the start date from certificate page (#2177)

Version 0.82.1 (Released April 12, 2021)
--------------

- Added configuration based digital credential support (#2182)

Version 0.82.0 (Released April 07, 2021)
--------------

- Updated receipts design and OS based Digital Credentials info text and store buttons (#2171)

Version 0.81.2 (Released April 05, 2021)
--------------

- Bump pygments from 2.4.2 to 2.7.4 (#2172)
- Bump rsa from 4.0 to 4.1 (#2166)
- Bump y18n from 4.0.0 to 4.0.1 (#2173)

Version 0.81.1 (Released March 29, 2021)
--------------

- Added digital credentials dialog and redirection (#2168)

Version 0.81.0 (Released March 26, 2021)
--------------

- Backend updates to support new DC UX
- Remove pytest-pylint (#2159)

Version 0.80.0 (Released March 19, 2021)
--------------

- Bump django from 2.2.13 to 2.2.18 (#2153)

Version 0.79.2 (Released March 17, 2021)
--------------

- Bump httplib2 from 0.18.0 to 0.19.0 (#2150)

Version 0.79.1 (Released March 17, 2021)
--------------

- Add digital credentials

Version 0.79.0 (Released March 11, 2021)
--------------

- Upgrade django-oauth-toolkit to 1.4.0 (#2124)
- Bump elliptic from 6.5.3 to 6.5.4 (#2146)
- Update B2B Email Receipt (#2142)

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
