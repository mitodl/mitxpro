import React from "react"

export const RadioButton = ({
  field: { name, value, onChange, onBlur },
  id,
  label,
  ...props
}) => {
  return (
    <div>
      <input
        name={name}
        type="radio"
        id={id}
        value={id}
        checked={id === value}
        onChange={onChange}
        onBlur={onBlur}
        {...props}
      />
      <label htmlFor={id}>{label}</label>
    </div>
  )
}

export const RadioButtonGroup = ({ className, children }) => {
  return <div className={className}>{children}</div>
}
