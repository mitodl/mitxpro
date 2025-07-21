# Wagtail API Documentation

This document describes the usage of the Wagtail-powered API for accessing course, program, and related metadata in xPRO.

## Overview

The Wagtail API exposes course, program, and related content as JSON.

**Base URL:**

- Local: `http://xpro.odl.local:8053/api/v2/`
- Staging/RC: `https://rc.xpro.mit.edu/api/v2/`
- Production: `https://xpro.mit.edu/api/v2/`

## Main Endpoints

### Course and Program Lists

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

### Filtering by Readable ID

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

### Accessing Images and Documents stored on Wagtail

- **Images:** `/images/`
- **Documents:** `/documents/`

## Field Selection

Use the `fields=*` query parameter to include all available fields in the response.

## Notes

- The API is public and does not require authentication.
- The base URL will differ depending on your environment (local, staging, production).
- For more details on the available fields and structure, inspect the API responses or refer to the Wagtail API documentation.

## References

- [Wagtail API v2 Documentation](https://docs.wagtail.org/en/6.4/advanced_topics/api/v2/usage.html)
