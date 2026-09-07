/**
 * Static metadata about the UserProfile fields, used by the write-time scheme
 * validator. Mirrors prisma/schema.prisma and docs/data-model.md.
 *
 * 12 fields: 8 required + 4 optional/nullable (land_holding,
 * paid_income_tax_last_year, monthly_pension, government_employee_grade).
 */

export const KNOWN_FIELDS = [
  "state",
  "age",
  "gender",
  "annual_family_income",
  "occupation",
  "education_level",
  "category",
  "support_type_needed",
  "land_holding",
  "paid_income_tax_last_year",
  "monthly_pension",
  "government_employee_grade",
] as const;

export type KnownField = (typeof KNOWN_FIELDS)[number];

/** Fields that hold a number. */
export const NUMERIC_FIELDS = [
  "age",
  "annual_family_income",
  "monthly_pension",
] as const;

/** Fields that hold a boolean. */
export const BOOLEAN_FIELDS = ["paid_income_tax_last_year"] as const;

export type NumericField = (typeof NUMERIC_FIELDS)[number];
export type BooleanField = (typeof BOOLEAN_FIELDS)[number];
export type EnumField = Exclude<KnownField, NumericField | BooleanField>;

export type FieldKind = "numeric" | "boolean" | "enum";

export const ALL_OPERATORS = [
  "equals",
  "not_equals",
  "in",
  "not_in",
  "gte",
  "lte",
  "exists",
  "not_exists",
] as const;

export type KnownOperator = (typeof ALL_OPERATORS)[number];

/** Operators allowed on numeric fields (age, annual_family_income, monthly_pension). */
export const NUMERIC_OPERATORS = ["gte", "lte", "exists", "not_exists"] as const;

/** Operators allowed on the boolean field (paid_income_tax_last_year). */
export const BOOLEAN_OPERATORS = [
  "equals",
  "not_equals",
  "exists",
  "not_exists",
] as const;

/** Operators allowed on enum fields (state, gender, occupation, land_holding, …). */
export const ENUM_OPERATORS = [
  "equals",
  "not_equals",
  "in",
  "not_in",
  "exists",
  "not_exists",
] as const;

export const INDIAN_STATES = [
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
] as const;

/** Allowed values for each enum field. */
export const ENUM_VALUES: Record<EnumField, readonly string[]> = {
  state: INDIAN_STATES,
  gender: ["male", "female", "other"],
  occupation: [
    "farmer",
    "student",
    "unemployed",
    "salaried",
    "self_employed",
    "other",
  ],
  education_level: [
    "below_10th",
    "10th_pass",
    "12th_pass",
    "graduate",
    "postgraduate",
    "other",
  ],
  category: ["general", "obc", "sc", "st", "ebc", "dnt", "other"],
  support_type_needed: [
    "financial_aid",
    "education",
    "healthcare",
    "housing",
    "employment",
    "agriculture",
    "business",
    "other",
  ],
  land_holding: ["none", "individual", "institutional"],
  government_employee_grade: [
    "not_applicable",
    "group_a_b_c",
    "group_d_mts",
  ],
};

export function isKnownField(value: unknown): value is KnownField {
  return (
    typeof value === "string" && (KNOWN_FIELDS as readonly string[]).includes(value)
  );
}

export function fieldKind(field: KnownField): FieldKind {
  if ((NUMERIC_FIELDS as readonly string[]).includes(field)) return "numeric";
  if ((BOOLEAN_FIELDS as readonly string[]).includes(field)) return "boolean";
  return "enum";
}

export function operatorsForKind(kind: FieldKind): readonly KnownOperator[] {
  if (kind === "numeric") return NUMERIC_OPERATORS;
  if (kind === "boolean") return BOOLEAN_OPERATORS;
  return ENUM_OPERATORS;
}
