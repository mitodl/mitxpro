// @flow
import React from "react"
import ReactMarkdown from "react-markdown"

// this is our patched version of react-markdown
// we need to fiddle with it to address this issue:
// https://github.com/rexxars/react-markdown/issues/115
// and also to block images

type MarkdownProps = {
  source: string
}

const Markdown = (props: MarkdownProps) => (
  <ReactMarkdown
    disallowedTypes={["image"]}
    escapeHtml
    className="markdown"
    renderers={{
      linkReference: reference =>
        reference.href ? (
          <a href={reference.$ref}>{reference.children}</a>
        ) : (
          <span>[{reference.children[0]}]</span>
        )
    }}
    {...props}
  />
)
export default Markdown
