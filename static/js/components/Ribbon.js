// @flow
import React from "react"

export const Ribbon = () => (
  <svg
    width="160"
    height="40"
    xmlns="http://www.w3.org/2000/svg"
    xmlnsXlink="http://www.w3.org/1999/xlink"
  >
    <g>
      <path
        id="svg_1"
        d="m21.99499,0.36536l137.77845,0l0,39.24426l-137.77845,0l0,-39.24426z"
      />
      <path
        transform="rotate(180 12.222884178161621,10.49860954284668)"
        id="svg_2"
        d="m2.10021,20.62128l0,-20.24534l20.24534,20.24534l-20.24534,0z"
      />
      <path
        id="svg_3"
        transform="rotate(-90 12.224372863769533,29.489900588989258)"
        d="m2.1017,39.61257l0,-20.24534l20.24535,20.24534l-20.24535,0z"
      />
    </g>
  </svg>
)

export const RibbonText = ({
  text,
  addedClasses
}: {
  text: string,
  addedClasses?: string
}) => (
  <div className={`text-ribbon ${addedClasses || ""}`}>
    <Ribbon />
    <div className="text">{text}</div>
  </div>
)
