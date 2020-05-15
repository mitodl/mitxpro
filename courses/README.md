xPRO Programs, Courses and Course Runs

**SECTIONS**
1. [How to create a new courserun](#how-to-create-a-new-courserun)

## How to create a new courserun

The course team will announce on the xpro_newcourses moira list, after the course has been created in edX Studio. The 
announcement should include at minimum the course id. Pricing information will be provided by the marketing team, usiing 
the same moira list. 

1. Create a program, if necessary

   1. Link to How to create a program TBD

2. Create a course if necessary 

   1. Link to How to create a course TBD
  
3. Create a courserun at /admin/courses/courserun/add/

   - **Course** choose from the drop down
   - **Title** should sync from xPRO Studio on a nightly basis. Or you can use the 
     management command `sync_courseruns` to do it immediately. 
   - **Courseware id** is the key for integration with open edX. It must be the same as the one used on xPRO Studiio
   - **Run tag** should be the last component of the course id, e.g. `R4`
   - **Courseware url** assuming this is an open edX course, the courseware path should be of the form 
     `/courses/{course id}/course/`. Note that this path is not validated. (See 
     https://github.com/mitodl/mitxpro/issues/1667)
   - all necessary dates will be pulled in automatically from xPRO Studio on a nightly basis. Or you can use the 
    management command `sync_courseruns` to do it immediately. 
   - Click save and note the courserun id, you will need it later. 
  
4. Create a product, if necessary, at /admin/ecommerce/product/add/

   a courserun without a product isn't much use. Users won't be able to enroll. 

   - set content type to Course Run 
   - Set object id to the courerun id from the courserun you created. 
   - Set `is_active` to true. Users cannot checkout with an inactive product
   - Set `availble_in_bulk_form` as appropriate. Private courses, demos and pilot courses should be set to false
   - Save the product and note the product id, you will need it later
   - Products are incomplete without a Product Version, create one at /admin/ecommerce/productversion/add/ 
     - Enter the product id for the product you just created
     - Set the price as directed by the course team. 
     - Set the description to be the same as the courserun title. The product title will appear on the checkout page
   - test the product by going to /checkout/?product= and the courserun id (text or integer)  

5. Check to make sure the course run in Studio has an appropriate professional track

   - go to /admin/coursemode in xPRO Studio
   - if a coursemode doesn't already exist for the courserun, add a new one
    
     - choose the course run from the drop-down list
     - choose the mode to "no-id-professional" from the drop-down
     - Set the name of the coursemode. By convention this is "Professional"
    
    