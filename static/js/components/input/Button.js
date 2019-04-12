// @flow
import React from "react"

type ButtonProps = {
  children: React$Element<*>,
  onClick: Function,
  className?: string
}

const Button = ({ children, onClick, className }: ButtonProps) => (
  <button className={`mdc-button ${className || ""}`} onClick={onClick}>
    {children}
  </button>
)

export default Button
