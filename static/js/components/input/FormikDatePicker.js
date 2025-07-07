import React, { useEffect, useState, useRef } from "react";
import { DayPicker } from "react-day-picker";
import { ErrorMessage } from "formik";
import { format, parse } from "date-fns";
import FormError from "../forms/elements/FormError";
import { zeroHour, finalHour } from "../../lib/util";

const FormikDatePicker = ({
  name,
  label,
  values,
  setFieldValue,
  setFieldTouched,
  endMonth = new Date(2099, 11),
}) => {
  const dateFormat = "MM/dd/yyyy";
  const fieldValue = values[name];
  const selectedDate = fieldValue ? new Date(fieldValue) : null;
  const [month, setMonth] = useState(selectedDate || new Date());
  const [showCalendar, setShowCalendar] = useState(false);
  const [inputValue, setInputValue] = useState(
    selectedDate ? format(selectedDate, dateFormat) : "",
  );
  const pickerRef = useRef(null);
  const fieldHourHandlers = {
    activation_date: zeroHour,
    expiration_date: finalHour,
  };

  useEffect(() => {
    if (fieldValue) {
      const date = new Date(fieldValue);
      if (
        date.getMonth() !== month.getMonth() ||
        date.getFullYear() !== month.getFullYear()
      ) {
        setMonth(date);
      }
      setInputValue(format(date, dateFormat));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fieldValue]);

  // Close calendar if clicked outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (pickerRef.current && !pickerRef.current.contains(event.target)) {
        setShowCalendar(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Check and apply date when full date is typed
  const handleInputChange = (e) => {
    const { value } = e.target;
    setInputValue(value);
    setFieldTouched(name, true);
    if (value.length === 0) {
      setFieldValue(name, null); // Reset field if input is cleared
      return;
    }
    if (value.length === 10) {
      const parsedDate = parse(value, dateFormat, new Date());
      if (!isNaN(parsedDate.getTime())) {
        fieldHourHandlers[name]?.(parsedDate);
        setFieldValue(name, parsedDate);
        setMonth(parsedDate);
      } else {
        setFieldValue(name, null); // Reset field if invalid date
      }
    }
  };

  return (
    <div className="block" ref={pickerRef} style={{ position: "relative" }}>
      <label htmlFor={name}>
        {label && <p style={{ marginBottom: "0.5rem" }}>{label}</p>}
      </label>
      <input
        id={name}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onClick={() => {
          setShowCalendar(!showCalendar);
          setFieldTouched(name, true);
        }}
        onBlur={() => setFieldTouched(name, true)}
      />

      {showCalendar && (
        <div className="date-picker-container">
          <DayPicker
            captionLayout="dropdown"
            mode="single"
            month={month}
            onMonthChange={setMonth}
            selected={selectedDate || undefined}
            onSelect={(value) => {
              if (value) {
                fieldHourHandlers[name]?.(value);
                setFieldValue(name, value);
                setInputValue(format(value, dateFormat));
                setFieldTouched(name, true);
                setShowCalendar(false);
              }
            }}
            endMonth={endMonth}
          />
        </div>
      )}

      <ErrorMessage name={name} component={FormError} />
    </div>
  );
};

export default FormikDatePicker;
