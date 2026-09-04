### Stripe

Stripe is one of the two payment gateways xPRO can use for B2C checkout. It is
chosen per user by a feature flag; anyone the flag is off for keeps using
CyberSource.

Everything below runs in Stripe's test mode. No real money moves.

#### 1. Get a Stripe test account

Sign up at [dashboard.stripe.com/register](https://dashboard.stripe.com/register).
It is free and takes a minute. You do not need to activate payments or provide
business details to use test mode.

Use your own account rather than sharing one. Test data stays yours, and each
account gets its own webhook secret, so nobody's local testing interferes with
anyone else's.

In the dashboard, make sure **Test mode** is on, then go to **Developers → API
keys** and copy the **Secret key**. It starts with `sk_test_`.

#### 2. Add settings

Add these to your `.env` file:

```
MITOL_PAYMENT_GATEWAY_STRIPE_API_KEY=sk_test_...
FEATURE_xpro-stripe-payments=True
```

| Setting                                | Value                     | Notes                                                                     |
| -------------------------------------- | ------------------------- | ------------------------------------------------------------------------- |
| `MITOL_PAYMENT_GATEWAY_STRIPE_API_KEY` | `sk_test_...`             | Your Stripe secret key from step 1.                                       |
| `FEATURE_xpro-stripe-payments`         | `True`, `False` (default) | Sends your checkouts to Stripe. Without it, checkout goes to CyberSource. |

Gateway selection reads the `xpro-stripe-payments` flag from PostHog and falls
back to `settings.FEATURES` when PostHog has no value for it, so the `.env`
setting is enough locally whether or not you have PostHog configured.

Restart the app after editing `.env`, and again after pulling new code:
the source is mounted into the container but the running server does not
reload it, so a change can appear on disk while the app still serves the
old version.

```
docker-compose restart web
```

#### 3. Install the Stripe CLI

On macOS:

```
brew install stripe/stripe-cli/stripe
```

For other platforms see
[Install the Stripe CLI](https://docs.stripe.com/stripe-cli/install).

Then connect it to your account:

```
stripe login
```

That opens your browser to confirm a pairing code.

#### 4. Forward webhooks to your machine

Stripe sends nothing back to the browser after payment. The order is only
fulfilled when the `checkout.session.completed` webhook arrives — without it
your order stays in `created` and the learner is never enrolled.

Stripe cannot reach your machine directly, so the CLI forwards events for you:

```
stripe listen --forward-to localhost:8053/api/checkout/stripe-webhook/
```

Leave this running in its own terminal while you test.

It prints a signing secret starting with `whsec_`. Webhook secrets are read from
the database rather than from settings, so store it once — either through Django
admin (**Payment Gateway → Stripe webhook secrets**, superusers only), or in a
shell:

```
docker-compose run --rm web ./manage.py shell
```

```python
from mitol.payment_gateway.models import StripeWebhookSecret, StripeWebhookSecretRoute

secret = StripeWebhookSecret.objects.create(
    secret_name="local stripe listen",  # any label you like
    webhook_secret="whsec_...",
    is_active=True,
)
StripeWebhookSecretRoute.objects.create(secret=secret, url_name="stripe-webhook")
```

If webhooks later start failing with `401`, the stored secret no longer matches
the one `stripe listen` is printing — update the row.

#### 5. Place a test payment

Go to checkout and pay with Stripe's
[test card](https://docs.stripe.com/testing) `4242 4242 4242 4242`, any future
expiry such as `12/34`, and any three-digit CVC.

After paying you land on a page that waits for the webhook, then forwards you to
your dashboard. You should see the enrollment there, and the event in the
`stripe listen` terminal.

#### Production setup

There is no `stripe listen` in a deployed environment. Instead, register the
endpoint once per environment in the Stripe dashboard, under **Developers →
Webhooks → Add endpoint**:

- **URL**: `https://<your-host>/api/checkout/stripe-webhook/`
- **Events**: `checkout.session.completed`, `checkout.session.expired`,
  `checkout.session.async_payment_succeeded`,
  `checkout.session.async_payment_failed`

Stripe shows the signing secret **once**, when the endpoint is created. Store it
in Django admin under **Payment Gateway → Stripe webhook secrets** (restricted to
superusers), adding a route with the url name `stripe-webhook` on the same form.

Without that row every webhook fails signature validation and returns `401`, so
learners are charged and their orders stay in `created`. It is worth confirming
the secret is present before enabling the Stripe flag for anyone.

To rotate a secret, add the new one and untick `is_active` on the old one. No
deploy is needed.

#### Recovering a stuck order

If a webhook never arrives, the order sits in `created`. `resolve_pending_orders`
asks the gateway what actually happened and makes our records match:

```
docker-compose run --rm web ./manage.py resolve_pending_orders --order xpro-b2c-dev-1
docker-compose run --rm web ./manage.py resolve_pending_orders --all
```

It only reports what it would do; pass `--commit` to apply the changes.
