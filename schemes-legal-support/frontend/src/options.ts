/**
 * Dropdown/radio option lists. `value` is exactly what the backend expects
 * (matches the Prisma enums); `label` is what the user sees.
 */
import type {
  EducationLevel,
  Gender,
  GovernmentEmployeeGrade,
  LandHolding,
  Occupation,
  SocialCategory,
  SupportType,
} from "./types";

export interface Option<T extends string = string> {
  value: T;
  label: string;
}

/** "Tamil_Nadu" -> "Tamil Nadu", "sc" -> "Sc" (used for enum-ish tokens). */
export function humanizeToken(token: string): string {
  return token
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export const INDIAN_STATES: Option[] = [
  "Andhra_Pradesh",
  "Arunachal_Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal_Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya_Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil_Nadu",
  "Telangana",
  "Tripura",
  "Uttar_Pradesh",
  "Uttarakhand",
  "West_Bengal",
  "Andaman_and_Nicobar_Islands",
  "Chandigarh",
  "Dadra_and_Nagar_Haveli_and_Daman_and_Diu",
  "Delhi",
  "Jammu_and_Kashmir",
  "Ladakh",
  "Lakshadweep",
  "Puducherry",
].map((value) => ({ value, label: value.replace(/_/g, " ") }));

export const GENDERS: Option<Gender>[] = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
];

export const OCCUPATIONS: Option<Occupation>[] = [
  { value: "farmer", label: "Farmer" },
  { value: "student", label: "Student" },
  { value: "unemployed", label: "Unemployed" },
  { value: "salaried", label: "Salaried employee" },
  { value: "self_employed", label: "Self-employed" },
  { value: "other", label: "Other" },
];

export const EDUCATION_LEVELS: Option<EducationLevel>[] = [
  { value: "below_10th", label: "Below 10th" },
  { value: "10th_pass", label: "10th pass" },
  { value: "12th_pass", label: "12th pass" },
  { value: "graduate", label: "Graduate" },
  { value: "postgraduate", label: "Postgraduate" },
  { value: "other", label: "Other" },
];

export const CATEGORIES: Option<SocialCategory>[] = [
  { value: "general", label: "General" },
  { value: "obc", label: "OBC" },
  { value: "sc", label: "SC" },
  { value: "st", label: "ST" },
  { value: "ebc", label: "EBC (Economically Backward Class)" },
  { value: "dnt", label: "DNT (Denotified / Nomadic Tribes)" },
  { value: "other", label: "Other" },
];

export const SUPPORT_TYPES: Option<SupportType>[] = [
  { value: "financial_aid", label: "Financial aid" },
  { value: "education", label: "Education" },
  { value: "healthcare", label: "Healthcare" },
  { value: "housing", label: "Housing" },
  { value: "employment", label: "Employment" },
  { value: "agriculture", label: "Agriculture" },
  { value: "business", label: "Business" },
  { value: "other", label: "Other" },
];

export const LAND_HOLDINGS: Option<LandHolding>[] = [
  { value: "none", label: "No land" },
  { value: "individual", label: "Individually held" },
  { value: "institutional", label: "Institutionally held" },
];

export const GOV_EMPLOYEE_GRADES: Option<GovernmentEmployeeGrade>[] = [
  { value: "not_applicable", label: "Not a government employee" },
  { value: "group_a_b_c", label: "Group A / B / C" },
  { value: "group_d_mts", label: "Group D / MTS" },
];

/** For the boolean field `paid_income_tax_last_year`. */
export const YES_NO: Option<"true" | "false">[] = [
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];
