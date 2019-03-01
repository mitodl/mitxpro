## Storing course data

### Abstract

The aim of this RFC is to make decisions about the following:
- The model definitions* that will be needed to store course data.
- The plan for loading legacy course data, and keeping that data current
  after we switch to using our own Open edX instance.

Out of scope for this RFC:
- Content management – we will just rely on Django admin for creating/updating
  courses by hand.
- Any kind of grading/certificate data.

\* - _Much like MicroMasters, we will keep our own models for courses/programs
  that will exist in parallel with the course data in edX_

### Models

Since this app has very similar needs, `Program`, `Course`, and `CourseRun` 
models will very closely mirror the [models in MicroMasters](https://github.com/mitodl/micromasters/blob/master/courses/models.py), 
minus a few fields that are not relevant for this app.

`Program`
- title
- description
- thumbnail (image)
- readable_id (string - will be used exclusively for reporting purposes)
- live (boolean - indicates whether the program is live in edX, et. al.)

`Course`
- program (`Program` foreign key, **nullable** since a course doesn't necessarily belong to a program)
- position_in_program (integer - indicates course sort order in a program)
- title
- description
- thumbnail (image)
- readable_id (string - will be used exclusively for reporting purposes)
- live (same as above)

`CourseRun`
- course (`Course` foreign key)
- courseware_id (string - the ID for the course run as it exists in
  the courseware platform, e.g.: an edX course key like `course-v1:MITxPRO+AMx+1T2019`)
- courseware_url (string - the URL for the course on the courseware platform)
- title
- start_date
- end_date
- enrollment_start
- enrollment_end
- live (same as above)

Some things to debate/pay particular attention to:

1. Programs/courses/course runs offered across different platforms

    We are still figuring out how legacy course data will be handled (for example, we don't yet
    know if we'll need to show a user's progress through a program that changed platforms). That
    will likely have some impact on the model structure, but for now we are not planning to
    record anything about the courseware platform where these objects were loaded from or where
    they currently exist.

1. `CourseRun.courseware_url`
    
    We need to be able to link directly to a course on its courseware
    platform. One option is to store the external id and, in our app logic,
    generate the link to the course based on that id and the platform it
    exists on (indicated by `source`). Another option is to simply store
    the external url alongside the external id. That involves some redundant
    data (the URL will almost certainly contain the external id), but the 
    external id is highly unlikely to change and we will gain some 
    flexibility, safety, and clarity by storing the URL separately. `CourseRun`s
    that exist on the legacy platform will have a null value for this column.

1. The `live` flag
    
    This is being added because we will want to be able to author some 
    information for programs/courses that don't yet exist on the courseware 
    platform.

### Loading Course Data

For the time being, the process of reflecting external course data in our
models can be broken down into 2 parts:
1. Loading legacy course data
1. Periodically updating course data from our Open edX instance

##### 1) Loading legacy course data

Still some decisions to be made here. There may be a separate RFC for this.
  
##### 2) Updating course data from Open edX

Once courses are being authored and managed in our own Open edX instance,
we'll need to keep our own models synced. 

**Proposal:** An asynchronous task that fetches edX course data via API and
updates/creates courses on our end (much like we do for enrollments/grades
in MicroMasters). 
