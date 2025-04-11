## External Course Sync Documentation

This document outlines the checks performed during the synchronization of external courses with our system.

### Setup Guide

The sync will not work if the platform doesn't exist in Django admin or enable sync checkbox is unchecked.

### External Course APIs

Below is a list of external vendor APIs which sync with our system:

- [Emeritus API](https://xpro.mit.edu/api/external_courses/emeritus/)
- [Global Alumni API](https://xpro.mit.edu/api/external_courses/global_alumni/)

### Required Fields Validation

Ensures that all required fields are present in the external course data.
If any required field is missing, that external course is skipped.
These fields are required for creating a course, course run, product, and product version.

**Required Fields:**

1. `course_title`
2. `course_code`
3. `course_run_code`
4. `list_currency`

### Currency Validation

Ensures the listing currency is `USD` (because the system only supports USD). If not, the external course is skipped.

### Course Run Dates Validation

Ensures that the course run dates are valid. If not, the external course is skipped.

- `start_date` must be provided and in the future.
- `end_date` must be later than `start_date` and in the future.

### Course Creation

Creates the course based on the external course data.

**Note:** We do not update the course object after that.

- If the course does not exist, it is created. Otherwise, we get it from the database.

### Course Run Creation or Update

Creates or Updates the course run based on the external course data.

#### Creation

- If the course run does not exist, it is created.
  - If `start_date` and `end_date` are present in the external data but `enrollment_end` is not present,
    then `enrollment_end` date is set to `start_date + 7 days`. This is done because external courses do not
    allow enrollments after the start date, and setting the enrollment end date to `start_date + 7 days` ensures
    a reasonable enrollment period while hiding the course run from the course details page after the enrollment period ends.

#### Update

- If the course run exists, it is updated with new data if necessary.
  - Fields Updated:
    - `start_date`
    - `end_date`
    - `enrollment_end`
    - `live`

### Product and Product Version Creation or Update

Creates or updates the product and product version for the course run
**if price is available in the external course data**

- If the product does not exist, it is created. We mark it as active when we update it.
- If the price does not exist or is different from the external course price, a new product version is created.

### External Course Page Creation or Update (CMS)

#### Creation

- If the external course page does not exist, it is created.

#### Update

- If the external course page exists, it is updated with new data if necessary.
  - **Fields updated**:
    - `external_marketing_url`
    - `duration`
    - `min_weeks`
    - `max_weeks`
    - `description`
    - `background_image`
    - `thumbnail_image`
    - `language`
- Background and thumbnail images are fetched from the existing images based on the image title
  that we get in the external course data. The image titles are expected to match the `title` field of the Wagtail Image model.

### Course Topic association

Associates the course with the existing topics based on the course category that we get in the external course data.

**Note:** We do not create new topics based on the external course data.

### Learning Outcomes Page Creation

If the learning outcomes page does not exist and there are learning outcomes in external course data, it is created.

**Note:** We do not update the learning outcomes page after that.

### Who Should Enroll Page Creation

If who should enroll page does not exist and there are who should enroll items, it is created.

**Note:** We do not update who should enroll page after that.

### Certificate Page Creation or Update

Creates or updates the certificate page for the course if CEUs are available in the external course data.

#### Creation

- If the certificate page does not exist, it is created.

#### Update

- If the certificate page exists, it is updated with new data if necessary.
  - Updated Fields:
    - CEUs

### Course Overview Page Creation

If the course overview page does not exist and there is a description in the external course data, it is created.

### Common How You Will Learn and Enterprise Page Creation

How You Will Learn and Enterprise pages are created if they do not exist.

- These are created based on the common child pages feature where we have common pages for all courses.

### Deactivation of Missing Course Runs and Products

If a course run is not present in the external course data, it is deactivated along with the product.
