# xPRO Google Sheets - Developer Setup

[Sheets README](./README.md)

**SECTIONS**

1. [Initial Setup](#initial-setup)
1. [Hacking](#hacking)
1. [Integrating with CI/RC](#integrating-with-ci-rc)

This guide contains instructions for hacking on the sheets feature in your own
development environment.

## Initial Setup

These are steps that only need to be completed once before you start hacking on this feature.

### 1) Dependencies

1. A Google account
1. [ngrok](https://ngrok.com/) – This is a tool that makes your localhost accessible
   to the wider internet. This is necessary for authenticating your locally-running
   xPRO app to make changes to your Google Drive files. If your app is deployed somewhere
   or you have an equivalent tool, ngrok isn't strictly necessary, but these instructions
   assume its use.

### 2) Configure credentials and permissions

1. Create an API project in Google Cloud Platform: https://console.cloud.google.com/home/dashboard
2. Create web application credentials for that project
   1. Visit the credential section of the Google Developer Console: https://console.developers.google.com/apis/credentials
   1. Click Create Credentials > OAuth client ID
   1. Select "Web application", give the credentials an intuitive name ("xPRO auth", et. al.), and submit.
3. Enable the Drive API for your project
   1. Visit the API console: https://console.developers.google.com/apis/library
   1. Select your Google Cloud Platform project from the dropdown at the top of the page.
   1. Find the Drive API, click on it, and enable it.

### 3) Copy an xPRO Drive project folder

An xPRO Drive folder should have the following artifacts:

1. **Spreadsheets** for each type of "request" we're servicing. As of 7/2020 that includes
   an enrollment code request spreadsheet, and an enrollment change request spreadsheet.
1. **Forms** for submitting new requests to those spreadsheets. As of 7/2020 that includes
   an enrollment code request form, a refund request form, and a deferral request form.
1. A **folder** which is the target for enrollment code assignment sheets that we generate.

**The contents of this folder should be copied from a "template" folder to a folder in your local Drive.**
There is a template folder on the MIT shared drive, or you can ask a fellow developer to share one.
**Just chat or email someone on the team to point you to one of these template folders.**
Once you can access a template folder, do the following to make your own copy:

1. Create a folder on your local Drive. Call it something like "Local xPRO Enrollments".
1. Create an empty subfolder for assignment sheets. Call it something like "Local Assignment Sheets".
1. In the template folder, select the spreadsheets (NOT the forms or any folders), and make a copy of them.
   - _NOTE: This will automatically create copies of the forms since the forms are linked to the spreadsheets already. This is intentional._
   - _ALSO NOTE: These spreadsheets each have a single test response already entered, and should be visible on the main worksheets. Leave those test responses where they are._
1. Select the copied spreadsheets _and_ forms, and move them to your xPRO enrollments folder that you created above.

Your Drive folder should look something like this when you're done:

![Enrollment Code Request form](images/sheets-drive-folder.png)

### 4) Add initial settings

First, gather a bunch of ID-type values from Drive:

1. The "Client ID" and "Client secret" values for the web application credentials you created
   above ([API Console Credentials section](https://console.developers.google.com/apis/credentials))
1. Your API project ID, which you can find in Google Cloud Platform > IAM & Admin > Settings > Project ID.
   Example: `my-api-project-1234567890123`
1. Drive file IDs for the request spreadsheets. These can be found by opening a spreadsheet from
   Drive and inspecting the URL. Example: `https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID_VALUE/edit#gid=0`.
   Copy the id for both the enrollment code request sheet and the change of enrollment sheet.
1. The IDs of the refund and deferral sheets in the change of enrollment spreadsheet. These can
   be found by opening the spreadsheet, selecting the "Refunds" or "Deferrals" worksheets, and
   copying down the `gid` value in the URL. Example: `https://docs.google.com/spreadsheets/d/abcd1234efgh5678bQFCQ7SSFBH5xHip0Gx2wPKT4fUA/edit#gid=THIS_IS_THE_WORKSHEET_ID`
1. The index of the first row where form-driven data begins in the refund and deferral worksheets.
   If you're starting with no data already filled in these sheets (recommended), just use the index
   of the first non-header row. Use the row index exactly as it appears in the spreadsheet.
1. The ID of the assignment sheet output folder. This can be found in a similar way to the
   spreadsheet IDs by opening the folder in Drive. Example: `https://drive.google.com/drive/u/0/folders/THIS_IS_THE_ID_VALUE`

_If it's not obvious, remove the angle brackets (`<>`) for the actual values._

```dotenv
SHEETS_ADMIN_EMAILS=<Your email address>
DRIVE_CLIENT_ID=<Client ID from step 1>
DRIVE_CLIENT_SECRET=<Client secret from step 1>
DRIVE_API_PROJECT_ID=<Project ID from step 2

COUPON_REQUEST_SHEET_ID=<Enrollment code request sheet ID from step 3>
ENROLLMENT_CHANGE_SHEET_ID=<Change of enrollment request sheet ID from step 3>
REFUND_REQUEST_WORKSHEET_ID=<Refund worksheet ID from step 4>
DEFERRAL_REQUEST_WORKSHEET_ID=<Deferral worksheet ID from step 4>
SHEETS_REFUND_FIRST_ROW=<Row index for the refund worksheet from step 6>
SHEETS_DEFERRAL_FIRST_ROW=<Row index for the deferral worksheet from step 6>
DRIVE_OUTPUT_FOLDER_ID=<Drive folder ID from step 5>
```

## Hacking

These are steps that will be relevant each time you want to use the sheets feature and
hack on it.

### Authenticating

Your local xPRO needs permissions to be able to read/write to your Drive. This can
be done via OAuth with the help of ngrok.

1. Run ngrok using the nginx port for this app: `ngrok http 8053`
1. Begin domain verification
   1. Visit Webmasters home: https://www.google.com/webmasters/verification/home?hl=en
   1. Enter the **HTTPS** URL that ngrok is exposing (use the full URL including the protocol)
   1. Select Alternate Methods > HTML Tag auth, and copy the "content" attribute value from tag (just the value, not the full HTML tag)
1. Update .env
   ```dotenv
   MITXPRO_BASE_URL=<Full ngrok HTTPS URL, including protocol; e.g.: https://12345abc6789.ngrok.io/ >
   GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE=<"content" attribute value from step 2.iii>
   ```
1. (Re)start containers
1. Click Verify in Domain verify page once containers are fully running. This should succeed.
1. Add Google API console configs ([API console link](https://console.cloud.google.com/apis/dashboard))
   1. Domain verification ([link](https://console.cloud.google.com/apis/credentials/domainverification)):
      Add the ngrok domain (e.g.: `12345abc6789.ngrok.io`)
   1. OAuth consent screen ([link](https://console.cloud.google.com/apis/credentials/consent))
      1. Click "Edit App"
      1. Add a domain in the "Authorized domains" section. **Hit Enter to add**.
      1. **Click Save at the bottom**
   1. Credentials ([link](https://console.cloud.google.com/apis/credentials))
      1. Click on the name of your web app credential in the OAuth 2.0 Client ID section
      1. In the "Authorized redirect URIs" section, click "Add URI", and enter the ngrok HTTPS URL appended with `/api/sheets/auth-complete/`, e.g.: `https://12345abc6789.ngrok.io/api/sheets/auth-complete/`
      1. **Click Save**
1. Log into xPRO via Django admin using the ngrok HTTP URL (e.g.: `http://12345abc6789.ngrok.io/admin/`)
1. Authenticate/authorize the app
   1. Navigate to the sheets admin page (`/sheets/admin/`) with the ngrok HTTP URL (e.g.: `http://12345abc6789.ngrok.io/sheets/admin/`)
   1. Click the Authorize button and go through Google OAuth flow
      - _NOTE: You will hit a warning page after selecting your user. To continue, click "Advanced", then click the "Go to \<url\>" link at bottom_

### Usage

In production, we have webhooks (also known as "file watches") set up to make a request
to xPRO so we can automatically execute some logic when a spreadsheet changes. You can set
those up locally too, but it's probably easier just to use the management commands.

Here's an example workflow for making a request for enrollment codes and assigning them:

1. Fill out and submit the enrollment code request form. The contract number and coupon name can
   be anything as long as they are not repeated from other submissions. This should add a row to the
   first worksheet in the enrollment code request spreadsheet.
1. Run the management command to process the sheet:
   `./manage.py process_coupon_requests -i "<Enrollment code request spreadsheet id>"`. This should
   update the "Date Processed" column for the row you added, and will create an assignment sheet in
   the target folder.
1. Open the enrollment code assignment sheet, and for one of the rows, enter the email address
   of some local app user.
1. Run the management command to process the assignment sheet:
   `./manage.py process_coupon_assignment_sheet -i "<Enrollment code assignment spreadsheet id>"`.
   This should update the given row to have a status of "assigned", and send an enrollment code
   email to you (if the email you entered is your own, or if you have the value of
   your `MAILGUN_RECIPIENT_OVERRIDE` setting is your email address).
1. When you receive the email, run the management command to update the message statuses in your
   assignment sheet:
   `./manage.py update_assignment_message_statuses --sheet-id "<Enrollment code assignment spreadsheet id>"`.
   This should update the assignment sheet row to have a status of "delivered".

## Integrating with CI/RC

Instead of using your own Drive folder and using OAuth to authenticate, you can
point your app at a Drive folder the we use for CI/RC. Apply the following changes
to your `.env` file:

- Remove or comment out the following settings: `GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE`,
  `DRIVE_CLIENT_ID`, `DRIVE_CLIENT_SECRET`, `DRIVE_API_PROJECT_ID`
- Add this setting, and ask a fellow developer or devops for the appropriate value:
  `DRIVE_SERVICE_ACCOUNT_CREDS`.
  - Example: `DRIVE_SERVICE_ACCOUNT_CREDS={"type": "service_account",  "project_id": "mitxpro",  "private_key_id": "abc123", "private_key": "-----BEGIN PRIVATE KEY-----\n..." ... }`
