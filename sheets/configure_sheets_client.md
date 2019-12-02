Google Sheets client configuration
---

These configuration steps will allow you to use Google Sheets to control the creation and 
assignment of bulk coupons.

**IMPORTANT LINKS**
- Google API Console: https://console.cloud.google.com/apis/dashboard
- Google Service Account Admin - https://console.cloud.google.com/iam-admin/serviceaccounts
- Google Webmaster Central - Domain Verification: https://www.google.com/webmasters/verification/home?hl=en

**HIGH-LEVEL STEPS**
1. [Create Drive folder and coupon request Sheet](#1-create-drive-folder-and-coupon-request-sheet)
1. [Add settings for Drive files](#2-add-settings-for-drive-files)
1. [Google API auth](#3-google-api-auth)
1. [Push notification setup](#4-push-notification-setup)


### 1) Create Drive folder and coupon request Sheet

The main driver of bulk coupon creation and assignment is the coupon request Sheet.
This Sheet needs to follow a specific format, so if this Sheet does not exist in the 
Drive you're working against, contact a fellow developer to have an example Sheet shared
with you so you can copy it. This Sheet should exist in a dedicated Drive folder. All coupon
assignment Sheets created from this app will also be placed in that folder.

### 2) Add settings for Drive files

```dotenv
# To get this value, load the coupon request sheet and check the url. 
# Example: `https://docs.google.com/spreadsheets/d/abcdefg012345678/edit#gid=0` – `abcdefg012345678` is the ID.
COUPON_REQUEST_SHEET_ID=my-request-sheet-id

# To get this value, navigate to the Drive folder where your request Sheet exists and 
# check the url. Example: `https://drive.google.com/drive/u/1/folders/abcdefg012345678` – `abcdefg012345678` is the ID.
DRIVE_OUTPUT_FOLDER_ID=my-output-folder-id

# Comma-separated list of emails of users that you would like to be invited as editors
# for each coupon assignment Sheet created. For testing, it's fine to just set this as your own email.
SHEETS_ADMIN_EMAILS=this@example.com,that@example.com 

# *NOTE:* 
# This is only needed if you're using a Shared Drive/Team Drive folder.
# This value is equal to the ID of the top-level folder in the Shared Drive,
# which can be found in the URL when viewing that folder.  
DRIVE_SHARED_ID=my-shared-drive-id
```

Optional settings that are good to know:

```dotenv
# Set this to a valid value in the TZ database if you want all dates in the spreadsheet
# to be assumed to be in that particular timezone.
SHEETS_DATE_TIMEZONE=America/New_York

# Set this to adjust the frequency that the coupon assignment spreadsheets will be
# checked for new/updated assignments and updated message statuses.
SHEETS_MONITORING_FREQUENCY=600
```

### 3) Google API auth

Authentication can be accomplished via OAuth (Authorization code flow) for a personal
Google account, or via Service Accounts
(Google documentation: [OAuth Authorization code](https://developers.google.com/identity/protocols/OAuth2WebServer), 
[Service Accounts](https://developers.google.com/identity/protocols/OAuth2ServiceAccount)).

**Follow one or the other of these auth methods, not both!**

#### Service Accounts  

##### a) Get Service Accounts credentials from devops or another developer

Devops, or a fellow developer, will have the Service Accounts credentials for
an MIT-owned Google account.

##### b) Add settings

Add these settings to your `.env` file

```dotenv
# This setting will be the contents of the credentials JSON file
# with all line breaks removed
DRIVE_SERVICE_ACCOUNT_CREDS={"type": "service_account", "project_id": "mitxpro", "private_key_id": ...}

# The SHEETS_ADMIN_EMAILS setting can include any number of personal email addresses
# for users that should be able to edit coupon assignment Sheets, but it MUST
# include the Service Account client email if you're using Service Accounts for auth. 
SHEETS_ADMIN_EMAILS=admin1@example.com,some-service-account-user@somesubdomain.iam.gserviceaccount.com
```

##### c) Share the bulk coupons Drive folder with the Service Account email

The Service Account user will need to be added with edit permissions.

#### Personal OAuth Authorization Code

##### a) Set up credentials in the Google API console

1. Create a project in the [API console](https://console.cloud.google.com/apis/dashboard), and select that project in the dropdown.
1. Enable the Google Sheets and Google Drive APIs in the dashboard ("Enable APIs and Services" button at the top of the 
   dashboard page)
1. In the "OAuth consent screen" section (link in left menu), add domains in the "Authorized domains"
   section
   - Examples: `xpro-rc.herokuapp.com`, `mit.edu`, `abcd1234.ngrok.io` (for local testing)
   - Be sure to click Save
1. In the "Credentials" section (link in left menu), click "Create Credentials" > "OAuth client ID"
   - Application type: "Web application"
   - Name: Your choice – Example: "mitxpro-sheets-app"
   - Authorized redirect URIs: Add an entry for every one of your Authorized Domains from the previous
     step with the protocol added, and add the path `/api/sheets/auth-complete/` to the end of each. 
     Examples: `https://xpro-rc.herokuapp.com/api/sheets/auth-complete/`, `https://xpro.mit.edu/api/sheets/auth-complete/`, ...
   - Be sure to click Save
1. Copy the `Client ID` and `Client secret` for that newly-created credential and set the values for the
   `DRIVE_CLIENT_ID` and `DRIVE_CLIENT_SECRET` mitxpro settings respectively.
1. Copy the API project ID and set the value of the `DRIVE_API_PROJECT_ID` mitxpro setting
   - The project ID can be found in the querystring of the [API console](https://console.cloud.google.com/apis/dashboard)
     dashboard as the value of the `project` parameter, e.g.: `my-project-1069972158283`)

##### b) Grant permissions from the mitxpro app

1. Run mitxpro and log in as an admin user
1. Go to `/sheets/admin/`, and click the button to kick off OAuth process
1. Grant permissions to the app to use the relevant APIs.
   - If running locally, you'll probably hit a page that says the app is untrusted, in which
     case you can click "Advanced" and proceed with authorization anyway.
   - If auth was successful, you should be brought back to that same admin page with a
     success message. There should also be a `GoogleApiAuth` record (which can be checked in Django admin).

##### c) Test the credentials

To test that API auth is set up correctly:
1. Add a row to the coupon request Sheet with the "Processed" column unchecked/`FALSE`
1. Run the `process_coupon_request_row` and point it at the row you just created
   via the transaction id and/or row number parameters.

The command should finish with a success message, the "Processed" column should now
be checked for the given row, your coupons should be created, a new coupon assignment
Sheet should have been created in the same folder as your coupon request Sheet, and
that new Sheet should be shared with the emails in your `SHEETS_ADMIN_EMAILS` setting.


### 4) Push notification setup

This requires the app to be publicly available. When running locally, that can
be accomplished by running something like [ngrok](https://ngrok.com). If using Service
Accounts for auth, the push notification setup will only work for domains that we own 
(i.e.: production/RC/CI, but not for PR builds hosted on herokuapp.com) 

##### a) Domain verification: 
1. Add a verified domain in [Google Webmaster Central](https://www.google.com/webmasters/verification/home?hl=en)
  - "Add A Property" > enter the full URL of your running mitxpro app > "Alternate Methods" > "HTML tag"
  - Copy the value of the `content` property of the `<meta>` tag in the section that drops down when
    you selected "HTML tag"
  - Set that as the value of the `GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE` mitxpro setting
  - If necessary, restart your app so the settings change takes effect
1. Click "Verify" in the Webmaster page once the running mitxpro app has the correct settings value
1. If verification was successful, unset the `GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE` setting as it is not needed anymore
1. Add the domain you just verified in the [Domain Verification section in API console](https://console.cloud.google.com/apis/credentials/domainverification)

##### b) Adding the push notification/webhook

Run the management command that make the file watch request to Google: `setup_request_sheet_file_watch`

If that management command indicates success, any rows added to the coupon request Sheet should
cause the mitxpro app to process that row (and any other row that has an unchecked "Processed" column).
If any of the rows are invalid/incomplete you should see an error in the logs, but the app will continue
to process other rows after logging the error.
