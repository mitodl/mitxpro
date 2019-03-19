// @flow
import { include } from "named-urls"
import qs from "query-string"

export const getNextParam = (search: string) => qs.parse(search).next || "/"

export const routes = {
  home: "",

  // authentication related routes
  login: "/login/",

  register: include("/signup/", {
    begin:   "",
    confirm: "confirm/",
    profile: "profile/"
  })
}
