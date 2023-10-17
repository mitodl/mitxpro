// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest } from "redux-query"
import { createStructuredSelector } from "reselect"


import queries from "../../lib/queries"
import type { Blogs } from "../../flow/blogTypes"

type Props = {
  blogs: Array<Blogs>,
}

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
                    <a href="https://learn-xpro.mit.edu/the-curve-subscribe">Subscribe</a>
                  </div>
                </div>
                <div className="recent-posts-heading">
                  <div className="editors-pick">Editor's Pick</div>
                  <div className="recent-posts-text">Top Most Recent Posts</div>
                </div>
                <div className="top-posts-container">
                  {featuredPost !== null ? (
                    <div className="featured-post-container" style={{background: `linear-gradient(180deg, rgba(0, 0, 0, 0.00) 0%, #A31F34 67.71%), url(${featuredPost.banner_image}) no-repeat`}}>
                      <div className="post-content">
                        <span className="post-tag">{featuredPost.category}</span>
                        <div className="featured-post-title">{featuredPost.title}</div>
                        <div className="featured-post-description">{featuredPost.description}</div>
                      </div>
                    </div>
                  ) : null}

                  <div className="posts-sidebar">
                    {
                      blogs !== null ? blogs.posts.slice(1).map(post => (
                        <div className="sidebar-post-card" key={post.guid}>
                          <img src={post.banner_image}/>
                          <div className="details">
                            <div className="post-title">{post.title}</div>
                            <div className="post-description">{post.description}</div>
                          </div>
                        </div>
                      )) : null
                    }
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
                      {blogs !== null ? blogs.categories.map(category => (
                        <div className="category slide" key={category}>
                          <a href="">{category}</a>
                        </div>
                      )) : null}
                    </div>
                    <div className="subscribe">
                      <a href="https://learn-xpro.mit.edu/the-curve-subscribe">Subscribe Now</a>
                    </div>
                  </div>
                </div>
                <div className="suggested-reading-heading">
                  <div className="from-mit">More From MIT</div>
                  <div className="suggested-readings">Suggested Readings</div>
                </div>
                <div className="posts-list">
                  {blogs !== null ? blogs.posts.map(post => (
                    <div className="post" key={post.guid}>
                      <div className="card-top">
                        <img src={post.banner_image} alt={post.title} />
                        <span className="post-tag">ONLINE EDUCATION</span>
                      </div>
                      <a className="title" href="">{post.title}</a>
                      <p className="description">{post.description}</p>
                      <div className="card-bottom">
                        <div className="author-and-duration">
                          <div className="author">BY: MIT XPRO | {post.published_date}</div>
                          <div className="duration">5 MINUTE READ</div>
                        </div>
                        <div className="read-more">
                          <a href="">READ MORE</a>
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
