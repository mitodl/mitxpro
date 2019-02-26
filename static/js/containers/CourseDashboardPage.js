// @flow
import React from "react"
import R from "ramda"
import { connect } from "react-redux"
import {
  connectRequest,
  querySelectors,
} from "redux-query"

class CourseDashboardPage extends React.Component<*, void> {
  render() {
    return (
      <div>
        <h2>Course Dashboard</h2>
      </div>
    )
  }
}

const mapStateToProps = state => (
  {}
)

export default R.compose(
  connect(mapStateToProps),
)(CourseDashboardPage)


// const booksRequest = (force = false) => ({
//   url:    "/api/library/books/",
//   update: {
//     books: (prev, next) => {
//       console.log("BOOKS")
//       console.log(prev)
//       console.log(next)
//       console.log("")
//       return next
//     },
//   },
//   transform: (responseJson, responseText) => {
//     console.log('responseJson')
//     console.log(responseJson )
//     console.log('responseText')
//     console.log(responseText)
//     return responseJson
//   },
//   force
// })
//
// class LibraryDashboardPage extends React.Component<*, void> {
//   props: {
//     dispatch: Dispatch<*>,
//     match: Match
//   }
//
//   render() {
//     const { isLoading, books } = this.props
//
//     console.log('books')
//     console.log(books)
//
//     return (
//       <div>
//         <h2>Library</h2>
//         {isLoading && <div><em>Loading...</em></div>}
//         {books && (
//           <div>BOOKS: {JSON.stringify(books)}</div>
//         )}
//       </div>
//     )
//   }
// }
//
// const mapStateToProps = state => {
//   return {
//     isLoading: querySelectors.isPending(state.queries, booksRequest()),
//     books:     state.entities.books
//   }
// }
//
// const mapPropsToConfigs = () => booksRequest()
//
// export default R.compose(
//   connect(mapStateToProps),
//   connectRequest(mapPropsToConfigs)
// )(LibraryDashboardPage)
