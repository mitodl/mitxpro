# xPro Google Sheets

**SECTIONS**
1. [What Is This?](#what-is-this)
1. [How It Works](#how-it-works)
1. [Types of Sheets](#types-of-sheets)
1. [Sheets Management](#sheets-management)
1. [Development Setup](#development-setup)

## What Is This?

We've had a few customer service-related use cases that we have needed to support. One option in terms of implementation
was to create several custom web UIs in xPro and give user access to all who needed it (CS representatives, finance 
team members, etc.) This had the potential to become a persistent headache for developers, so we decided to support 
these use cases through UIs that are very familiar to most users regardless of technical expertise: Google Sheets and
Google Forms. Using various Google Drive and Sheets APIs, the following is now possible: 

1. CS/finance users can make various requests (e.g.: enrollment code creation/assignment, enrollment deferrals) by filling 
  out a Google Form or entering data into Google Sheets.
1. Those requests are automatically processed by our app.
1. Users can monitor the status of their requests directly in the spreadsheets.  

## How It Works

The basic workflow for most flavors of xPro sheets is roughly as follows:

1. A user fills out a Google Form. That form submission is a request for some work to 
be done, and it is automatically added to a form responses worksheet within a relevant spreadsheet.
    - That submission also appears in the main worksheet within the spreadsheet automatically via a query.
1. In response to the change in the spreadsheet, Google sends a file watch request to an endpoint in our app, which 
  indicates to us that the spreadsheet has been changed, so we may have some new requests to handle.
1. Our app scans the main worksheet of the spreadsheet for new or updated rows and takes the appropriate action if the
  data is all valid (e.g.: issuing a refund, creating new enrollment codes, etc.)
1. If a request was completed for some row, or if an error occurred, our app updates certain columns in the 
  main worksheet to indicate the status of that request.  

## Types of Sheets

Right now there are three sheet types:

1. Enrollment Code Request sheet (a.k.a. Coupon Request sheet)
1. Enrollment Code Assignment sheets (which are created based on Enrollment Code Request sheet entries)
1. Change of Enrollment Request sheet. This includes worksheets for the following:
    1. Refund Requests
    1. Deferral Requests

#### Enrollment Code Request Sheet & Assignment Sheets

_Details to be filled in later..._

#### Enrollment Change Requests (Refunds, Deferrals)

_Details to be filled in later..._

## Sheets Management

One cardinal rule to follow for all of the "request"-type sheets: **Do not edit the main worksheet directly, unless the 
columns exist specifically for user input**. Examples of columns that are intended for user input are the Finance 
columns in the Change of Enrollment sheets.

The terms "main worksheet" and "form responses worksheet" are used below. Here are some
screenshots for explanation.

**Enrollment Code Request worksheet tabs:**
![Enrollment Code Request worksheet tabs](images/enrollment-code-worksheet-tabs.png)

**Change of Enrollment Request worksheet tabs:**
![Change of Enrollment Request worksheet tabs](images/change-of-enrollment-worksheet-tabs.png)

#### Editing Rows

**When you'll want to edit:** there is some bad data in a form submission (a typo, a naming conflict, etc).

**How to do it:** Find the row in the relevant "Form Responses" worksheet that matches the row in the main 
spreadsheet and directly edit the columns there. 

Example scenario: On the Enrollment Code Request spreadsheet, some row has some detail in the Errors column indicating that a
user doesn't exist due to a misspelled email address. To fix this, you would go to the "Form Responses" worksheet 
(which holds the the raw response data from the form), find the row that matches the one you saw on the main worksheet
with the error text, and updated the email column value there. 

Google sends file watch requests to our app if anything in the spreadsheet is edited, so those changes to the Form
Responses data should be handled automatically.

#### Ignoring Rows 

**Request rows cannot be deleted, only set to "ignored".** There are a couple different reasons for this. 
 
**When you'll want to set a row to ignored:** The request is no longer relevant (for example, the request is an accidental repeat). 

**How to do it:** Find the row in the relevant Form Responses worksheet that matches the
row on the main worksheet** (check the "Editing Rows" section for details), **and enter `=TRUE` into the "Ignored?" 
column of that row in the Form Responses worksheet.** 

Ignored rows will be greyed out on the main worksheet, and the app will automatically skip over all request rows that 
are set to ignored. 

#### Interpreting the rows

_Details to be filled in later..._

## Development Setup

_Details to be filled in later..._
