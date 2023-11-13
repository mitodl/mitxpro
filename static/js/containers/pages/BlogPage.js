// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest } from "redux-query"
import { createStructuredSelector } from "reselect"


import queries from "../../lib/queries"


export class BlogPage extends React.Component<Props> {
  render() {
    const { blogs } = this.props
    const featuredPost = blogs !== null ? blogs.posts[0] : null

    return (
      <React.Fragment>
        <DocumentTitle
          title={`${SETTINGS.site_name} | Blog`}
        >
          <div className="blog-page">
            <div className="blog-header">
              <div className="heading-container">
                <h1 className="heading">Blog</h1>
                <p className="title">Online learning stories for professionals, from MIT</p>
              </div>
              <div className="subscribe">
                <a href="https://learn-xpro.mit.edu/the-curve-subscribe">Subscribe Now</a>
              </div>
            </div>
            <div className="most-recent-posts">
              <div className="recent-posts-heading">Top Most Recent Posts</div>
              <div className="recent-posts-container">
                <div className="posts-list">
                  {blogs !== null ? blogs.posts.map(post => (
                    <div className="post" key={post.guid}>
                      <div className="card-top">
                        <img src={post.banner_image} alt={post.title} />
                        <div className="post-tags">
                          {post.categories.map(tag => (
                            <span className="tag" key={tag}>{tag}</span>
                          ))}
                        </div>
                      </div>
                      <a className="title" href={post.link}>{post.title}</a>
                      <p className="description">{post.description}</p>
                      <div className="card-bottom">
                        <div className="author-and-duration">
                          <div className="author">BY: MIT XPRO | {post.published_date}</div>
                          <div className="duration">5 MINUTE READ</div>
                        </div>
                        <div className="read-more">
                          <a href={post.link}>READ MORE</a>
                        </div>
                      </div>
                    </div>
                  )) : null}
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
  blogs: queries.blog.blogsSelector,
})

const mapPropsToConfigs = () => [
  queries.blog.blogsQuery(),
]

export default compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfigs)
)(BlogPage)
