// @flow
import React from "react"
import R from "ramda"
import { connect } from "react-redux"
import type { Match } from "react-router"
import type { Dispatch } from "redux"
import {
  connectRequest,
  querySelectors,
} from "redux-query"

class LibraryDashboardPage extends React.Component<*, void> {
  props: {
    dispatch: Dispatch<*>,
    match: Match
  }

  render() {
    const { isLoading, books } = this.props

    console.log('books')
    console.log(books)

    return (
      <div>
        <h2>Library</h2>
        {isLoading && <div><em>Loading...</em></div>}
        {books && (
          <div>BOOKS: {JSON.stringify(books)}</div>
        )}
      </div>
    )
  }
}

const mapStateToProps = state => {
  return {
    isLoading: querySelectors.isPending(state.queries, booksRequest()),
    books:     state.entities.books
  }
}

const mapPropsToConfigs = () => booksRequest()

export default R.compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfigs)
)(LibraryDashboardPage)
