## External Course Sync Documentation

This document outlines the checks performed during the synchronization of external courses to create, update, or skip the internal models.

### External Course APIs

For reference, the external course APIs are:

- [Emeritus API](https://xpro.mit.edu/api/external_courses/emeritus/)
- [Global Alumni API](https://xpro.mit.edu/api/external_courses/global_alumni/)

### Required Fields Validation

Ensures that all required fields are present in the external course data. If any of the required fields are missing, the external course is skipped.

Required Fields: `course_title, course_code, course_run_code, list_currency`

### Currency Validation

Ensures that the price is in `USD`. Only USD is supported. If the currency is not USD, the external course is skipped.

### End Date Validation

Ensures that the course `end_date` is in the future. If the course end date is in the past, the external course is skipped.

### Course Creation

Creates the course based on the external course data. **Note:** We do not update the course object after that.

- If the course does not exist, it is created. Otherwise, we get it from the database.

### Course Run Creation or Update

Creates or Updates the course run based on the external course data.

- If the course run does not exist, it is created.
  - `start_date` and `end_date` are present in the external data but `enrollment_end` is not present, then enrollment end date is set to the start date. This is done because external courses do not allow enrollments after the start date, and setting the enrollment end date to the start date hides the course run from the course details page.
- If the course run exists, it is updated with new data if necessary.
- Updated Fields:
  - `start_date`
  - `end_date`
  - `enrollment_end`
  - `live`

### Product and Product Version Creation or Update

Creates or updates the product and product version for the course run **if price is available in the external course data**

- If the product does not exist, it is created. We mark it as active when we update it.
- If the price does not exist or is different from the external course price, a new product version is created.

### External Course Page Creation or Update

- If the external course page does not exist, it is created.
- If the external course page exists, it is updated with new data if necessary.
- Updated Fields:
  - external_marketing_url
  - duration
  - min_weeks
  - max_weeks
  - description
  - background_image
  - thumbnail_image
  - language
- Background and thumbnail images are fetched from the existing images based on the image title that we get in the external course data. The image titles are expected to match the `title` field of the Wagtail Image model.

### Course Topic association

Associates the course with the existing topics based on the course category that we get in the external course data.

### Learning Outcomes Page Creation

If the learning outcomes page does not exist and there are learning outcomes in external course data, it is created.

### Who Should Enroll Page Creation

If the who should enroll page does not exist and there are who should enroll items, it is created.

### Certificate Page Creation or Update

Creates or updates the certificate page for the course if CEUs are available in the external course data.

- If the certificate page does not exist, it is created.
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
