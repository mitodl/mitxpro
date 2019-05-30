// Put constants here

export const COUPON_TYPE_PROMO = "promo"
export const COUPON_TYPE_SINGLE_USE = "single-use"

export const PRODUCT_TYPE_PROGRAM = "program"
export const PRODUCT_TYPE_COURSE = "course"
export const PRODUCT_TYPE_COURSERUN = "courserun"
export const PRODUCT_TYPE_LABELS = {
  [PRODUCT_TYPE_PROGRAM]:   "Program",
  [PRODUCT_TYPE_COURSE]:    "Course",
  [PRODUCT_TYPE_COURSERUN]: "Course Run"
}

export const GENDER_CHOICES = [
  ["m", "Male"],
  ["f", "Female"],
  ["o", "Other/Prefer Not to Say"]
]

export const EMPLOYMENT_INDUSTRY = [
  "Association, Nonprofit Organization, NGO",
  "Business and Professional Services",
  "Construction and Engineering",
  "Education",
  "Energy",
  "Financials",
  "Government / Armed Forces",
  "Food, Beverages and Tobacco",
  "Government",
  "Health Care",
  "Industrials",
  "Retailing",
  "Materials",
  "Media",
  "Information technology",
  "Transportation",
  "Other",
  "Prefer not to say"
]

export const EMPLOYMENT_EXPERIENCE = [
  [2, "Less than 2 years"],
  [5, "2-5 years"],
  [10, "6 - 10 years"],
  [15, "11 - 15 years"],
  [20, "16 - 20 years"],
  [21, "More than 20 years"],
  [0, "Prefer not to say"]
]

export const EMPLOYMENT_SIZE = [
  [1, "Small/Start-up (1+ employees)"],
  [9, "Small/Home office (1-9 employees)"],
  [99, "Small (10-99 employees)"],
  [999, "Small to medium-sized (100-999 employees)"],
  [9999, "Medium-sized (1000-9999 employees)"],
  [10000, "Large Enterprise (10,000+ employees)"],
  [0, "Other (N/A or Don't know)"]
]

export const EMPLOYMENT_FUNCTION = [
  "Accounting",
  "Administrative",
  "Arts and Design",
  "Business Development/Sales",
  "Community & Social Services",
  "Consulting",
  "Education",
  "Engineering",
  "Entrepreneurship",
  "Finance",
  "Healthcare Services",
  "Human Resources",
  "Information Technology",
  "Legal",
  "Media/Communications/Marketing",
  "Military & Protective Services",
  "Operations",
  "Program & Product Management",
  "Purchasing",
  "Quality Assurance",
  "Real Estate",
  "Research",
  "Support",
  "Other"
]

export const EMPLOYMENT_LEVEL = [
  "Upper Management",
  "Middle Management",
  "Junior First Line Management",
  "Individual Contributor",
  "Consultant/Contractor",
  "Temporary Employee",
  "Other",
  "Prefer not to say"
]
