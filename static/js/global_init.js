// Define globals we would usually get from Django
import ReactDOM from "react-dom"
import { configure } from "enzyme"
import Adapter from "enzyme-adapter-react-16"

configure({ adapter: new Adapter() })

const _createSettings = () => ({})

global.SETTINGS = _createSettings()
global.TESTING = true
global.CSOURCE_PAYLOAD = null

// polyfill for Object.entries
import entries from "object.entries"
if (!Object.entries) {
  entries.shim()
}

// cleanup after each test run
// eslint-disable-next-line mocha/no-top-level-hooks
afterEach(function() {
  const node = document.querySelector("#integration_test_div")
  if (node) {
    ReactDOM.unmountComponentAtNode(node)
  }
  document.body.innerHTML = ""
  global.SETTINGS = _createSettings()
  window.location = "http://fake/"
})

// enable chai-as-promised
import chai from "chai"
import chaiAsPromised from "chai-as-promised"
chai.use(chaiAsPromised)
