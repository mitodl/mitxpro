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
1. [Google API auth](#2-google-api-auth)
1. [Push notification setup](#3-push-notification-setup)


### 1) Create Drive folder and coupon request Sheet

The main driver of bulk coupon creation and assignment is the coupon request Sheet.
This Sheet needs to follow a specific format, so if this Sheet does not exist in the 
Drive you're working against, contact a fellow developer to have an example Sheet shared
with you so you can copy it. That Sheet should exist in a separate Drive folder. All coupon
assignment Sheets created from this app will also be placed in that folder.

**⚠️ NOTE: You can make changes to this Sheet manually to test this feature, but in production, 
we will only want to allow (1) this app, and (2) a Google Form to make changes to the Sheet. 
That permission scheme is still a work in progress, so for now, changes to the coupon request Sheet
can be manually applied. ⚠️**

### 2) Google API auth

Authentication can be accomplished via OAuth (Authorization code flow) or by setting
up a service account
(Google documentation: [OAuth Authorization code](https://developers.google.com/identity/protocols/OAuth2WebServer), 
[Service Accounts](https://developers.google.com/identity/protocols/OAuth2ServiceAccount)).

**Follow one or the other of these auth methods, not both!**

#### OAuth Authorization Code

##### 2a) Set up credentials in the Google API console

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

##### 2b) Grant permissions from the mitxpro app

1. Run mitxpro and log in as an admin user
1. Go to `/sheets/admin/auth/`, and click the button to kick off OAuth process
1. Grant permissions to the app to use the relevant APIs.
   - If running locally, you'll probably hit a page that says the app is untrusted, in which
     case you can click "Advanced" and proceed with authorization anyway.
   - If auth was successful, you should be brought back to that same admin page with a
     success message. There should also be a `GoogleApiAuth` record (which can be checked in Django admin).

##### 2c) Add mitxpro settings values

The following settings values should already be set from previous steps:
`DRIVE_CLIENT_ID`, `DRIVE_CLIENT_SECRET`, `DRIVE_API_PROJECT_ID`.

These additional settings must also be added:
- `COUPON_REQUEST_SHEET_ID`: To get this value, load the coupon request sheet and check the url. 
  Example: `https://docs.google.com/spreadsheets/d/abcdefg012345678/edit#gid=0` – `abcdefg012345678` is the ID.
- `DRIVE_OUTPUT_FOLDER_ID`: To get this value, navigate to the Drive folder where your request Sheet exists and 
  check the url. Example: `https://drive.google.com/drive/u/1/folders/abcdefg012345678` – `abcdefg012345678` is the ID.
- `SHEETS_ADMIN_EMAILS`: Comma-separated list of emails of users that you would like to be invited as editors
  for each coupon assignment Sheet created. For testing, it's fine to just set this as your own email. 

*NOTE: If you're testing this in a CI PR build, you may also need to change the `MITXPRO_BASE_URL`
setting from `https://xpro-ci.herokuapp.com` to `https://xpro-ci-pr-<YOUR_PR_NUMBER>.herokuapp.com`*  

##### 2d) Test the credentials

To test that API auth is set up correctly:
1. Add a row to the coupon request Sheet with the "Processed" column unchecked/`FALSE`
1. Run the `process_coupon_request_row` and point it at the row you just created
   via the transaction id and/or row number parameters.

The command should finish with a success message, the "Processed" column should now
be checked for the given row, your coupons should be created, a new coupon assignment
Sheet should have been created in the same folder as your coupon request Sheet, and
that new Sheet should be shared with the emails in your `SHEETS_ADMIN_EMAILS` setting.

#### Service Accounts  

TBD

### 3) Push notification setup

1. Add a verified domain in [Google Webmaster Central](https://www.google.com/webmasters/verification/home?hl=en)
  - "Add A Property" > enter the full URL of your running mitxpro app > "Alternate Methods" > "HTML tag"
  - Copy the value of the `content` property of the `<meta>` tag in the section that drops down when
    you selected "HTML tag"
  - Set that as the value of the `GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE` mitxpro setting
  - If necessary, restart your app so the settings change takes effect
1. Click "Verify" in the Webmaster page once the running mitxpro app has the correct settings value
1. If verification was successful, unset the `GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE` setting as it is not needed anymore
1. Add the domain you just verified in the [Domain Verification section in API console](https://console.cloud.google.com/apis/credentials/domainverification)
1. Run the management command that make the file watch request to Google: `setup_sheet_update_webhook`

If that management command indicates success, any rows added to the coupon request Sheet should
cause the mitxpro app to process that row (and any other row that has an unchecked "Processed" column).
If any of the rows are invalid/incomplete you should see an error in the logs, but the app will continue
to process other rows after logging the error.
