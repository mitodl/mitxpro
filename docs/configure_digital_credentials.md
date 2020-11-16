### Digital Credentials


#### Architecture

Digital Credentials depends on a few external components existing:

- An instance of the [`sign-and-verify`](https://github.com/digitalcredentials/sign-and-verify) service
- A mobile-based Digital Credentials Wallet app (To Be Implemented)

To have a learner get a signed digital credential, the following workflow occurs:

- When either a course run or program certificate is created, a digital credentials request is also created
- xPro then asynchronously sends a notification email to the learner with a deep like to the wallet app
  - This deep link includes url parameters (endpoint urls mostly) for the wallet app that detail how to perform the next few steps
- The wallet app navigates the learner to xPro website to initiate an OAuth2 login, specifying a deep link redirect url for completion of the authentication flow
- The learner logs in, authorizes the OAuth2 request, and is then redirected to another deep link into the wallet app
- This second deep link contains a short term auth token which the wallet app exchanges for an access token
- This access token is limited in permissions to ONLY allow the digital credentials endpoint to be called
- The wallet app then performs a request to the digital credentials endpoint using this access token
  - This results in a call to the `sign-and-verify` service from xPro using information about the certificate that has been issues to the learner plus some learner identity information sent from the wallet app


#### Settings


| Setting | Value | Notes |
|---|---|---|
| `DIGITAL_CREDENTIALS_DEEP_LINK_URL` | `dcwallet://deep_link` | The deep link url to the digital credentials wallet app. This will typically involve a custom url scheme. |
| `DIGITAL_CREDENTIALS_ISSUER_ID` | - | The digital credentials issuer id to be included in the credential template. This value is determined by the digital credentials team. |
| `DIGITAL_CREDENTIALS_VERIFICATION_METHOD` | - | The digital credentials verification method to be included in the credential template. This value is determined by the digital credentials team. |
| `MITOL_DIGITAL_CREDENTIALS_HMAC_SECRET` | - | Any random string, MUST match the corresponding HMAC secret `sign-and-verify` is deployed with. |
| `MITOL_DIGITAL_CREDENTIALS_VERIFY_SERVICE_BASE_URL` | `http://sign-and-verify.example.com:5678/` | The addressable base url for the `sign-and-verify` service. |


#### Runtime configuration

The wallet app requires an oauth application to be configured in django-admin.

#### Feature flags

We will ONLY turn these on when we're ready to enable the feature in production:

| Setting | Value | Notes |
|---|---|---|
| `FEATURE_DIGITAL_CREDENTIALS` | `True`, `False` (default)| Enables the generation of digital credential requests, the prerequisite to being able to generate and sign digital credentials. The corresponding code is triggered when program and course certificates are generated. |
| `FEATURE_DIGITAL_CREDENTIALS_EMAIL` | `True`, `False` (default)| Enables the sending of email notifications for digital credential requests. |
