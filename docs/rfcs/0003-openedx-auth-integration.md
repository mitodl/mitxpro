## Open edX Auth Integration

#### Abstract

We need to be able to authenticate MIT xPro users with our hosted version of Open edX.

- User should not have to take any manual effort (e.g. entering a password) to login to Open edX
- This will _probably_ need to be some flavor of OAuth where MIT xPro is the OAuth Service Provider

We need to make a decision on where we want the user identity source of truth for this application to live. Options that are available to us are:

- **Open edX**
  - Pros:
    - Users can login to Open edX without having to go through xPro first
  - Cons:
    - Speculation: this *might* complicate the story around merging user data in xPro regarding pulling in historical data from edX.org
    - Users will be subject to the same Discussions -> xPro -> edX -> xPro -> Discussions authentication flow that MicroMasters currently has
    - We'd need to figure out how to direct the user to xPro for purchasing and enrolling
  - Pro/Con?:
    - Open edX is the primary application for the user, xPro acts like a portal similar to MicroMasters
- **xPro** - Select Option
  - Pros:
    - Identity is not tied to Open edX, so we can swap out that system in the future without having to rebuild our identity system as a prerequisite
    - For xPro users to login to Discussions, this requires one less application hop than the Open edX identity strategy
  - Cons:
    - If we decide to integrate this product with Discussions, we'll need to figure out a better solution than the JWT-based auth system that MicroMasters currently utilizes, which has been the source of a fair amount of difficult bugs
    - We need to figure out how to securely create the user in Open edX without requiring the user to register there
- **Open Discussions**
  - We've previously discussed having Discussions be our primary identity service for all our apps
  - Pros:
    - Consolidates user/profile information in one place
    - Gives end users access to Discussions out of the gate
  - Cons:
    - Requires work on the Discussions app
    - For local development, running both Discussions and xPro is required
  - Known Unknowns:
    - Where/how will users update/modify their user/profile information?


#### Architecture Changes

##### Write a OAuth2 Provider library for Open edX

Open edX supports additional custom OAuth2 providers that `python-social-auth` doesn't support out of the box as documented [here](https://edx.readthedocs.io/projects/edx-installing-configuring-and-running/en/latest/configuration/tpa/tpa_integrate_open/tpa_oauth.html#additional-oauth2-providers-advanced). This would involve writing and publishing to pypi a module that has our implementation in it.

##### Enable MIT xPro as an OAuth2 Service Provider

The most straightforward solution is to use [`django-oauth-toolkit`](https://django-oauth-toolkit.readthedocs.io/en/latest/) to accomplish this.

##### xPro creates account in Open edx

xPro will perform an API request to edX's user registration endpoint to create the user and social-auth linkages:

```
curl \
  --data-urlencode "username=USERNAME" \
  --data-urlencode "email=user@example.com" \
  --data-urlencode "name=FirstName LastName" \
  --data-urlencode "country=US" \
  --data-urlencode "honor_code=True" \
  --data-urlencode "provider=mitxpro-oauth2" \
  --data-urlencode "access_token=ACCESS_TOKEN" \
  http://openedx.dev.local:18000/user_api/v1/account/registration/
```

xPro will then call Open edX's APIs to create an access token for itself so that it can authenticate to edX APIs on behalf of the user for enrollment, grades, etc.

#### Security Considerations

The above implementation changes utilize standard and well-tested libraries to get us 95% of the way there. The majority of security concerns will be around secret sharing or any highly custom behavior we need to stack on top of these frameworks.

#### Testing & Rollout

These suggestions still need a Proof of Concept to verify that they work in practice but generally speaking this is a turnkey solution. Each environment will need to be configured as we roll out these integrations and we should strive to automate developer environment setups as much as possible.
