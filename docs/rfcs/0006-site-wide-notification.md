## Site Wide Notifications

#### Abstract

As a member of the marketing team, I'd like to be able to post a message that will appear on all pages of the site, for example to advertise a promotion.

#### Requirements

- Brief description of the plan for adding, editing and removing the site-wide notification (see options below)
- CMS user can add, edit and remove banner message through Wagtail. Or, if that is difficult, admin user can add, edit and remove banner message through the django admin
- User can dismiss the banner by clicking on the X. It should stay hidden for the rest of the session.

##### Out of scope (Will do in future)

- Date range between which the content should be displayed
- Ensure that only one site wide notification can be displayed at once (@pdpinch I'm guessing we want this to avoid overwhelming the user?)

##### Designs and Mockups
- See, for example, [InVision](https://impactbnd.invisionapp.com/share/4TQEESTEYMZ#/screens/345573039)
- This element should also be in the [course PSD](https://drive.google.com/file/d/10uAQ3emiF3ufd5eigYow0kxwA_51WiVD/view?usp=sharing)

#### Architecture Changes

##### Backend changes

- Add snippet `SiteNotification` in wagtail with following field
    - notification

- Add templatetag to render notifications.
- Add templatetag in base.html


##### Frontend changes

 - Use `sessionStorage` to save state of the User.
 - Show notification only when `notificationDisplayed` value is `null` in `sessionStorage`.
 
#### Security Considerations
Only authenticated and authorized user can access `MarkNotificationViewed`

#### Testing & Rollout
Unit tests will be added to test this feature. 