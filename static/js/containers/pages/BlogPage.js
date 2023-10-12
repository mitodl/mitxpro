// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"


import { addUserNotification } from "../../actions"
import queries from "../../lib/queries"
import users, { currentUserSelector } from "../../lib/queries/users"


export class BlogPage extends React.Component {

  render() {
    return (
      <React.Fragment>
        <DocumentTitle
          title={`${SETTINGS.site_name} | Blog`}
        >
          <div className="blog-page">
            <div className="recent-posts-container">
              <div className="header-and-recent-posts">
                <div className="header">
                  <div className="blog-heading">
                    <div className="blog-heading-bold">
                      The Curve: An online learning blog
                    </div>
                    <div className="blog-heading-normal">
                      for professionals, from MIT
                    </div>
                  </div>
                  <div className="subscribe">
                    <a href="">Subscribe</a>
                  </div>
                </div>
                <div className="recent-posts-heading">
                  <div className="editors-pick">Editor's Pick</div>
                  <div className="recent-posts-text">Top Most Recent Posts</div>
                </div>
                <div className="top-posts-container">
                  <div className="featured-post-container" style={{background: "linear-gradient(180deg, rgba(0, 0, 0, 0.00) 0%, #A31F34 67.71%), url(/static/images/rectangle-2.png) no-repeat"}}>
                    <div className="post-content">
                      <span className="post-tag">ONLINE EDUCATION</span>
                      <div className="featured-post-title">The Competitive Advantages of Online Corporate LearningThe Competitive Advantages of Online Corporate Learning</div>
                      <div className="featured-post-description">Online corporate learning is one of the most effective ways to deepen your team’s knowledge and expand their abilities regarding everything from the most ground-breaking emerging technologies</div>
                    </div>
                  </div>
                  <div className="posts-sidebar">
                    <div className="sidebar-post-card">
                      <img src="/static/images/mit-dome.png"/>
                      <div className="details">
                        <div className="post-title">What to Read Next: Recommendations from MIT xPRO Faculty</div>
                        <div className="post-description">ONLINE EDUCATION What to Read Next: Recommendations from MIT xPRO Faculty</div>
                      </div>
                    </div>
                    <div className="sidebar-post-card">
                      <img src="/static/images/mit-dome.png"/>
                      <div className="details">
                        <div className="post-title">What to Read Next: Recommendations from MIT xPRO Faculty</div>
                        <div className="post-description">ONLINE EDUCATION What to Read Next: Recommendations from MIT xPRO Faculty</div>
                      </div>
                    </div>
                    <div className="sidebar-post-card">
                      <img src="/static/images/mit-dome.png"/>
                      <div className="details">
                        <div className="post-title">What to Read Next: Recommendations from MIT xPRO Faculty</div>
                        <div className="post-description">ONLINE EDUCATION What to Read Next: Recommendations from MIT xPRO Faculty</div>
                      </div>
                    </div>
                    <div className="sidebar-post-card">
                      <img src="/static/images/mit-dome.png"/>
                      <div className="details">
                        <div className="post-title">What to Read Next: Recommendations from MIT xPRO Faculty</div>
                        <div className="post-description">ONLINE EDUCATION What to Read Next: Recommendations from MIT xPRO Faculty</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="all-posts-container">
              <div className="all-posts">
                <div className="categories-section">
                  <div className="container">
                    <div className="categories-header">
                      Explore more from&nbsp;
                      <div className="bold">MIT xPRO Categories</div>
                    </div>
                    <div className="row category-slider">
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                      <div className="category slide" data-url="">
                        <a href="">Category</a>
                      </div>
                    </div>
                    <div className="subscribe">
                      <a href="">Subscribe Now</a>
                    </div>
                  </div>
                </div>
                <div className="suggested-reading-heading">
                  <div className="from-mit">More From MIT</div>
                  <div className="suggested-readings">Suggested Readings</div>
                </div>
                <div className="posts-list">
                  <div className="post">
                    <div className="card-top">
                      <img src="/static/images/mit-dome.png" alt="Preview image" />
                      <span className="post-tag">ONLINE EDUCATION</span>
                    </div>
                    <a className="title" href="">What to Read Next: Recommendations from MIT xPRO Faculty</a>
                    <p className="description">Wondering what to read next? Ready to stimulate your brain with topics ranging from systems engineering to artificial intelligence? You’ve come to the right place.</p>
                    <div className="card-bottom">
                      <div className="author-and-duration">
                        <div className="author">BY: MIT XPRO | JUNE 7TH, 2023</div>
                        <div className="duration">5 MINUTE READ</div>
                      </div>
                      <div className="read-more">
                        <a href="">READ MORE</a>
                      </div>
                    </div>
                  </div>
                  <div className="post">
                    <div className="card-top">
                      <img src="/static/images/mit-dome.png" alt="Preview image" />
                      <span className="post-tag">ONLINE EDUCATION</span>
                    </div>
                    <a className="title" href="">What to Read Next: Recommendations from MIT xPRO Faculty</a>
                    <p className="description">Wondering what to read next? Ready to stimulate your brain with topics ranging from systems engineering to artificial intelligence? You’ve come to the right place.</p>
                    <div className="card-bottom">
                      <div className="author-and-duration">
                        <div className="author">BY: MIT XPRO | JUNE 7TH, 2023</div>
                        <div className="duration">5 MINUTE READ</div>
                      </div>
                      <div className="read-more">
                        <a href="">READ MORE</a>
                      </div>
                    </div>
                  </div>
                  <div className="post">
                    <div className="card-top">
                      <img src="/static/images/mit-dome.png" alt="Preview image" />
                      <span className="post-tag">ONLINE EDUCATION</span>
                    </div>
                    <a className="title" href="">What to Read Next: Recommendations from MIT xPRO Faculty</a>
                    <p className="description">Wondering what to read next? Ready to stimulate your brain with topics ranging from systems engineering to artificial intelligence? You’ve come to the right place.</p>
                    <div className="card-bottom">
                      <div className="author-and-duration">
                        <div className="author">BY: MIT XPRO | JUNE 7TH, 2023</div>
                        <div className="duration">5 MINUTE READ</div>
                      </div>
                      <div className="read-more">
                        <a href="">READ MORE</a>
                      </div>
                    </div>
                  </div>
                  <div className="post">
                    <div className="card-top">
                      <img src="/static/images/mit-dome.png" alt="Preview image" />
                      <span className="post-tag">ONLINE EDUCATION</span>
                    </div>
                    <a className="title" href="">What to Read Next: Recommendations from MIT xPRO Faculty</a>
                    <p className="description">Wondering what to read next? Ready to stimulate your brain with topics ranging from systems engineering to artificial intelligence? You’ve come to the right place.</p>
                    <div className="card-bottom">
                      <div className="author-and-duration">
                        <div className="author">BY: MIT XPRO | JUNE 7TH, 2023</div>
                        <div className="duration">5 MINUTE READ</div>
                      </div>
                      <div className="read-more">
                        <a href="">READ MORE</a>
                      </div>
                    </div>
                  </div>
                  <div className="post">
                    <div className="card-top">
                      <img src="/static/images/mit-dome.png" alt="Preview image" />
                      <span className="post-tag">ONLINE EDUCATION</span>
                    </div>
                    <a className="title" href="">What to Read Next: Recommendations from MIT xPRO Faculty</a>
                    <p className="description">Wondering what to read next? Ready to stimulate your brain with topics ranging from systems engineering to artificial intelligence? You’ve come to the right place.</p>
                    <div className="card-bottom">
                      <div className="author-and-duration">
                        <div className="author">BY: MIT XPRO | JUNE 7TH, 2023</div>
                        <div className="duration">5 MINUTE READ</div>
                      </div>
                      <div className="read-more">
                        <a href="">READ MORE</a>
                      </div>
                    </div>
                  </div>
                  <div className="post">
                    <div className="card-top">
                      <img src="/static/images/mit-dome.png" alt="Preview image" />
                      <span className="post-tag">ONLINE EDUCATION</span>
                    </div>
                    <a className="title" href="">What to Read Next: Recommendations from MIT xPRO Faculty</a>
                    <p className="description">Wondering what to read next? Ready to stimulate your brain with topics ranging from systems engineering to artificial intelligence? You’ve come to the right place.</p>
                    <div className="card-bottom">
                      <div className="author-and-duration">
                        <div className="author">BY: MIT XPRO | JUNE 7TH, 2023</div>
                        <div className="duration">5 MINUTE READ</div>
                      </div>
                      <div className="read-more">
                        <a href="">READ MORE</a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DocumentTitle>
      </React.Fragment>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  enrollments: queries.enrollment.enrollmentsSelector,
  currentUser: currentUserSelector
})

const mapPropsToConfigs = () => [
  queries.enrollment.enrollmentsQuery(),
  users.currentUserQuery()
]

const requestDigitalCredentials = (uuid: string, isCourse: boolean) =>
  requestAsync({
    ...queries.digitalCredentials.requestDigitalCredentials(uuid, isCourse),
    force: true
  })

const mapDispatchToProps = {
  requestDigitalCredentials,
  addUserNotification
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfigs)
)(BlogPage)
