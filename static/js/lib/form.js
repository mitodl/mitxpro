// @flow
import type { CheckoutPayload } from "../flow/ecommerceTypes"
import React from "react"

/**
 * Creates a POST form with hidden input fields
 * @param url the url for the form action
 * @param payload Each key value pair will become an input field
 */
export function createCyberSourceForm(
  url: string,
  payload: CheckoutPayload
): HTMLFormElement {
  const form = document.createElement("form")
  form.setAttribute("action", url)
  form.setAttribute("method", "post")
  form.setAttribute("class", "cybersource-payload")

  for (const key: string of Object.keys(payload)) {
    const value = payload[key]
    const input = document.createElement("input")
    input.setAttribute("name", key)
    input.setAttribute("value", value)
    input.setAttribute("type", "hidden")
    form.appendChild(input)
  }
  return form
}

export const formatErrors = (
  errors: string | Object | null
): React$Element<*> | null => {
  if (!errors) {
    return null
  }

  let errorString
  if (typeof errors === "object") {
    if (errors.items) {
      errorString = errors.items[0]
    } else {
      errorString = errors[0]
    }
  } else {
    errorString = errors
  }
  return <div className="error">{errorString}</div>
}
