Configure Open edX
---

In order to create user accounts in Open edX and permit authentication from xPro to Open edX, you need to configure xPro as an OAuth2 provider for Open edX.


#### Setup Open edX Devstack

Follow devstack's [README instructions](https://github.com/edx/devstack#getting-started) to get a functional devstack instance running.

#### Install `social-auth-mitxpro` in LMS

There are two options for this:

##### Install via pip

- `pip install social-auth-mitxpro`

##### Install from local Build

- Checkout the [social-auth-mitxpro](https://github.com/mitodl/social-auth-mitxpro) project and build the package per the project instructions
- Copy the `social-auth-mitxpro-$VERSION.tar.gz` file into devstack's `edx-platform` directory
- In devstack, run `make lms-shell` and within that shell `pip install social-auth-mitxpro-$VERSION.tar.gz`
  - To update to a new development version without having to actually bump the package version, simply `pip uninstall social-auth-mitxpro`, then install again


#### Configure xPro as a OAuth provider for Open edX

In xPro:

- go to `/admin/oauth2_provider/application/` and create a new application with these settings selected:
  - `Redirect uris`: `http://<EDX_HOSTNAME>:18000/auth/complete/mitxpro-oauth2/`
  - `Client type`: "Confidental"
  - `Authorization grant type`: "Authorization code"
  - `Skip authorization`: checked
  - Other values are arbitrary but be sure to fill them all out. Save the client id and secret for later

In Open edX (derived from instructions [here](https://edx.readthedocs.io/projects/edx-installing-configuring-and-running/en/latest/configuration/tpa/tpa_integrate_open/tpa_oauth.html#additional-oauth2-providers-advanced)):
- `make lms-shell` into the LMS container and ensure the following settings:
  - `/edx/app/edxapp/lms.env.json`:
    ```
    {
      ...
      "FEATURES": {
        ...
        "ENABLE_THIRD_PARTY_AUTH": true,
        ...
      },
      ...
      "THIRD_PARTY_AUTH_BACKENDS": ["social_auth_mitxpro.backends.MITxProOAuth2"],
      ...
    }
    ```
  - `/edx/app/edxapp/lms.auth.json`:
    ```
    {
      ...
      "SOCIAL_AUTH_OAUTH_SECRETS": {
        "mitxpro-oauth2": "<xpro_application_client_secret>"
      },
      ...
    }
    ```
- `make lms-restart` to pick up the configuration changes
- Login to django-admin, go to `http://<EDX_HOSTNAME>:8000/admin/third_party_auth/oauth2providerconfig/`, and create a new config:
  - Select the default example site
  - The slug field **MUST** match the `Backend.name`, which for us is `
mitxpro-oauth2`
  - Check the following checkboxes:
    - Skip hinted login dialog
    - Skip registration form
    - Sync learner profile data
    - Enable SSO id verification
  - In "Other settings", put:
    ```
    {
        "AUTHORIZATION_URL": "http://<LOCAL_XPRO_ALIAS>:8053/oauth2/authorize/",
        "ACCESS_TOKEN_URL": "http://<EXTERNAL_XPRO_HOST>:8053/oauth2/token/",
        "API_ROOT": "http://<EXTERNAL_XPRO_HOST>:8053/"
    }
    ```
    - `LOCAL_XPRO_ALIAS` should be your `/etc/hosts` alias for the mitxpro app
    - `EXTERNAL_XPRO_HOST` will depend on your OS, but it needs to be resolvable within the edx container
        - Linux users: The gateway IP of the docker-compose networking setup for xPro as found via `docker network inspect mitxpro_default`
        - OSX users: Use `host.docker.internal`
