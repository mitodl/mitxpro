# Wagtail API Documentation

This document describes the usage of the Wagtail-powered API for accessing course, program, and related metadata in xPRO.

## Overview

The Wagtail API exposes course, program, and related content as JSON.

**API Endpoint:**

- Path: `/api/v2/`

## Course and Program Lists

- **Internal Course List:**
  - `/pages/?fields=*&type=cms.coursepage`
- **External Course List:**
  - `/pages/?fields=*&type=cms.externalcoursepage`
- **Program List:**
  - `/pages/?fields=*&type=cms.programpage`
- **External Program List:**
  - `/pages/?fields=*&type=cms.externalprogrampage`

All list endpoints are paginated (default: 20 per page). Use `limit` and `offset` query parameters to control pagination:

- `?limit=50&offset=20`

## Filtering by Readable ID

To fetch details for a specific course or program, filter by the `readable_id` field:

```
GET /pages/?fields=*&readable_id=<readable_id>&type=cms.CoursePage
```

Replace `<readable_id>` with the desired value, e.g.:

```
GET /pages/?fields=*&readable_id=course-v1:edX+DemoX+Demo_Course&type=cms.CoursePage
```

Supported types:

- `cms.CoursePage`
- `cms.ProgramPage`
- `cms.ExternalCoursePage`
- `cms.ExternalProgramPage`

## Accessing Images and Documents

- **Images:** `/images/`
- **Documents:** `/documents/`

## Field Selection

Use the `fields=*` query parameter to include all available fields in the response.

## Accessing the API (OAuth2 Authentication)

Access to the Wagtail API requires staff authentication using OAuth2.

### For Local Development

#### Create a Staff User

1. In Django admin, go to **Users** and create a new user with `is_staff=True` and `is_active=True`
2. Set a password for the user

#### Create an OAuth2 Application

1. In Django admin, add a new **Application** (under "OAuth2 Provider")
2. Fill in:
   - **Name**: (e.g., "Wagtail API Test")
   - **User**: (the staff user you just created)
   - **Client type**: `Confidential`
   - **Authorization grant type**: `Resource owner password-based`
   - **Check Skip Authorization**
   - **Redirect URIs**: (leave blank for password grant)
3. Save and note the **Client ID** and **Client Secret**

### For Production/Staging

Ask xPRO developers for:

- **Client ID** and **Client Secret**
- **Username** and **Password** for a staff user

### 1. Obtain an Access Token

Use the OAuth2 Resource Owner Password Credentials grant to obtain a token:

```
curl -X POST </oauth2/token/ \
  -d "grant_type=password" \
  -d "username=<your-username>" \
  -d "password=<your-password>" \
  -d "client_id=<your-client-id>" \
  -d "client_secret=<your-client-secret>"
```

The response will include an `access_token` and `refresh_token`.

### 2. Use the Access Token

Include the access token in the `Authorization` header for all API requests:

```
curl -H "Authorization: Bearer <access_token>" \
     https://<your-domain>/api/v2/pages/?fields=*&type=cms.coursepage
```

You should receive a JSON response if your credentials and token are valid.

## References

- [Wagtail API v2 Documentation](https://docs.wagtail.org/en/6.4/advanced_topics/api/v2/usage.html)
