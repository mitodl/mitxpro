# xPRO: Programs, Program Runs, Courses, and Course Runs

**SECTIONS**
* [How to create a Program](#how-to-create-a-program)
* [How to create a Program Run](#how-to-create-a-program-run)
* [How to create a Course](#how-to-create-a-course)
* [How to create a Course Run](#how-to-create-a-course-run)

## How to create a Program

1. **Create a program** at: `/admin/courses/program/add/`
  - **Title**: the title of the program
  - **Readable id**: e.g. `program-v1:xPRO+SysEngx`
  - **Live**: check to make live


## How to create a Program Run

1. **[Create a Program](#how-to-create-a-program)** if necessary

2. **Create a program run**
  - If you're creating a new program or a complete set of course runs for a given program, you should create a new program run at `/admin/courses/programrun/add/`
  - **Program**: choose the correct program, e.g. `Architecture and Systems Engineering: Models and Methods to Manage Complex Systems`
  - **Run tag**: the run tag, e.g. `R11`
  - **Start date**: enter the start date for the earliest course in the program. Start time is `05:00:00` by convention.
  - **End date**: enter the end date for the latest course in the program. End time is `23:30:00` by convention.


## How to create a Course
1. **[Create a Program](#how-to-create-a-program)** if necessary

2. **[Create a Program Run](#how-to-create-a-program-run)** if necessary 
 
3. **Create a new course** at: `/admin/courses/course/add/`
  - **Program**: if the course is a part of a program, select it from the pulldown
  - **Position in program**: if in a program, set the order in the list of courses in the program (1 to x)
  - **Title**: the title of the course, e.g. `Leading Change in Organizations`
  - **Readable id**: the id, e.g. `course-v1:xPRO+LASERx3`
  - **Live**: Set to live when ready to launch. Note that you should not check this box for courses that will not need a catalog page, e.g. a SPOC or a private course. 
  - **Topics**: select the applicable topic(s)



## How to create a Course Run

The course team will announce on the xpro_newcourses moira list, after the course has been created in edX Studio. The announcement should include at minimum the course id. Pricing information will be provided by the marketing team, usiing the same moira list. 

1. **[Create a Program](#how-to-create-a-program)** if necessary

2. **[Create a Program Run](#how-to-create-a-program-run)** if necessary 

3. **[Create a Course](#how-to-create-a-course)** if necessary
 
4. **Create a course run** at `/admin/courses/courserun/add/`
  - **Course**: choose from the drop down
  - **Title**: should be the title of the course. Note this value should sync from xPRO Studio on a nightly basis. You can also use the management command `sync_courseruns` to do it immediately. 
  - **Courseware id**: is the key for integration with open edX. It must be the same as the one used on xPRO Studiio, e.g. `course-v1:xPRO+SysEngx1+R4`
  - **Run tag**: should be the last component of the course id, e.g. `R4`
  - **Courseware url**: assuming this is an open edX course, the courseware path should be of the form 
     `/courses/{course id}/course/`. Note that this path is not validated. (See 
     https://github.com/mitodl/mitxpro/issues/1667)
  - all necessary dates will be pulled in automatically from xPRO Studio on a nightly basis. Or you can use the management command `sync_courseruns` to do it immediately. 
  - **Live**: should be unchecked until you're ready to make the course run live. This value determines if the start date will appear in the list of options for the course page in the CMS. 
  - **Save** and note the courserun id, you will need it later. 

  
5. **Create a product**, if necessary, at `/admin/ecommerce/product/add/` (required for enrollment)
  - **Content type**: set to Course Run 
  - **Object id**: set to the courerun id from the course run you created. 
  - **Is active**: Set `Is active` to true. Note that this needs to be set to check the checkout for the product version (below). If checked, the product start date will appear in the pulldown on the checkout page. You may want to uncheck it after testing until you're ready to launch.
  - **Visible in bulk form**: Set `Visible in bulk form` as appropriate. Private courses, demos and pilot courses should be set to false
  - **Save** the product and note the product id, you will need it later


6. **Create a product version**, if created a product, at `/admin/ecommerce/productversion/add/` 
  - **Product**: Enter the product id for the product you just created
  - **Price**: Set the price as directed by the course team. 
  - **Description**: Set the description to be the same as the course run title. The product title will appear on the checkout page
  - **Test** the product by going to `/checkout/?product=` and the course run id (text or integer)  


7. **Professional Track**: Check to make sure the course run in Studio has an appropriate professional track. New course runs in Studio default to audit track. The track doesn't actually make a difference, but users get confusing messages about auditing and certificates in open-edx if they are in an audit track. May eventually be addressed by issue #973.
  - go to `/admin/course_modes/` in xPRO Studio
  - click on 'course modes'
  - if a coursemode doesn't already exist for the course run, select Add Course Mode    
    - choose the course run from the drop-down list
    - choose the mode to `no-id-professional` from the drop-down
    - Set the name of the coursemode. By convention this is `Professional`
    - No need to set any of the other values
  - After creating the mode, run management command to force users into the new role, e.g. `retry_edx_enrollment --run course-v1:xPRO+QCFx2+R5 --force`


8. **Access Codes**: 
  - Test staff and team codes on the checkout page to ensure they'll work. Note that if a team code has expired, you should set the expiration date to be after the last run for that course. 
  - You may need to add coupon eligibilities if necessary.


9. **Data Consent Agreement**:
  - You may need to set up a data consent agreement for this course
  - Go to `/admin/ecommerce/dataconsentagreement/` and click on `ADD DATA CONSENT AGREEMENT`
  - Enter the 
    - **Content** - you can likely copy much of it from an existing one
    - **Company** - choose from the pull-down
    - **Courses** - a comma-separated list of course id's
  - Click `SAVE`
  - Note: To test the data consent agreement, you'll need to enter an enrollment code associated with the same company as the data consent agreement on the checkout page. You should see a checkbox asking you to agree to the data consent agreement before you can proceed with the purchase. 

