# Data Model

This document is the source of truth for the two core schemas in the Schemes &
Legal Support app:

- **UserProfile** — the fixed set of fields a user fills in during intake.
- **Scheme** — a government scheme plus its structured, machine-checkable
  eligibility data.

The matching engine (built later) takes one `UserProfile` and evaluates it
against every `Scheme.eligibility` tree. Nothing in this document describes that
engine; it only fixes the shapes both sides agree on.

The Prisma implementation of the scalar fields lives in
[`../backend/prisma/schema.prisma`](../backend/prisma/schema.prisma). The nested
`eligibility` condition tree is stored as a single `jsonb` column and is
specified here (Prisma does not model it).

---

## A) UserProfile

The first 8 fields are **required**; the 4 fields below the rule (added later,
from gaps found converting real schemes) are **optional / nullable**. All enum
values are lower `snake_case` unless noted. The **field key** column is the
canonical name a `Scheme` eligibility leaf condition refers to via its `field`
property — these must match exactly.

For **every** field — required or optional — `null` / `undefined` means
"unknown / not provided": a leaf condition on that field evaluates to
`"unknown"` (not `"fail"`) unless its operator is `exists` / `not_exists`.
The only difference for the 4 optional fields is that a stored `UserProfile`
row is allowed to leave them `null`.

| Field key              | Type   | Values / notes |
|------------------------|--------|----------------|
| `state`                | enum   | One of the 36 Indian states / UTs. See [IndianState](#indianstate). |
| `age`                  | number | Integer years. Non-negative. |
| `gender`               | enum   | `male` \| `female` \| `other` |
| `annual_family_income` | number | Whole rupees (INR), household total. Non-negative. |
| `occupation`           | enum   | `farmer` \| `student` \| `unemployed` \| `salaried` \| `self_employed` \| `other`. Extensible — see note below. |
| `education_level`      | enum   | `below_10th` \| `10th_pass` \| `12th_pass` \| `graduate` \| `postgraduate` \| `other` |
| `category`             | enum   | `general` \| `obc` \| `sc` \| `st` \| `ebc` \| `dnt` \| `other`. Social category, for reservation-based eligibility (very common in Indian schemes). `ebc` (Economically Backward Class) and `dnt` (Denotified / Nomadic Tribes) are legally distinct groups with their own schemes (e.g. PM-YASASVI) — **not** subsets of `obc`. |
| `support_type_needed`  | enum   | `financial_aid` \| `education` \| `healthcare` \| `housing` \| `employment` \| `agriculture` \| `business` \| `other` |
| `land_holding`             | enum, nullable    | `none` \| `individual` \| `institutional`. Whether the family holds cultivable land and in what capacity. `institutional` = land held by a body/trust/company rather than a person. |
| `paid_income_tax_last_year`| boolean, nullable | `true` if the family paid income tax in the last assessment year. Used by exclusion rules (e.g. PM-KISAN excludes income-tax payers). |
| `monthly_pension`          | number (INR), nullable | Monthly pension amount received, in whole rupees. `0` is a real value (receives no pension); `null` = not provided. |
| `government_employee_grade`| enum, nullable    | `not_applicable` \| `group_a_b_c` \| `group_d_mts`. Serving/retired government post grade. `not_applicable` = not a government employee; `group_d_mts` = Group D / Multi-Tasking Staff (often exempted from exclusions that hit `group_a_b_c`). |

### TypeScript shape

```ts
interface UserProfile {
  state: IndianState;
  age: number;
  gender: "male" | "female" | "other";
  annual_family_income: number; // INR, whole rupees
  occupation:
    | "farmer"
    | "student"
    | "unemployed"
    | "salaried"
    | "self_employed"
    | "other";
  education_level:
    | "below_10th"
    | "10th_pass"
    | "12th_pass"
    | "graduate"
    | "postgraduate"
    | "other";
  category: "general" | "obc" | "sc" | "st" | "ebc" | "dnt" | "other";
  support_type_needed:
    | "financial_aid"
    | "education"
    | "healthcare"
    | "housing"
    | "employment"
    | "agriculture"
    | "business"
    | "other";

  // Optional / nullable. `null` | undefined = unknown / not provided.
  land_holding?: "none" | "individual" | "institutional" | null;
  paid_income_tax_last_year?: boolean | null;
  monthly_pension?: number | null; // INR, whole rupees; 0 is a real value
  government_employee_grade?:
    | "not_applicable"
    | "group_a_b_c"
    | "group_d_mts"
    | null;
}
```

### Extending `occupation` (and other enums)

`occupation` is expected to grow. To add a value:

1. Add the member to the `Occupation` enum in `schema.prisma` and run a
   migration.
2. Add it to the table and the TypeScript union above.
3. `other` stays as the catch-all until a value is common enough to earn its
   own member.

The same procedure applies to any enum here; `occupation` is just the one most
likely to need it.

---

## B) Scheme

| Field                  | Type                     | Notes |
|------------------------|--------------------------|-------|
| `scheme_id`            | string (unique)          | Stable human-readable slug, e.g. `pm-kisan`. External reference / URL segment. |
| `name`                 | string                   | Official scheme name. |
| `short_summary`        | string                   | One–two sentence plain-language description. |
| `level`                | enum                     | `Central` \| `State` |
| `state`                | enum \| null             | An [IndianState](#indianstate). **Set only when `level = State`**; `null` for Central schemes. |
| `category`             | string[]                 | Free-form domain tags, e.g. `["agriculture", "income-support"]`. Not the same as `UserProfile.category`. |
| `eligibility`          | object (`jsonb`)         | `{ hard, soft }` — two [condition trees](#eligibility-condition-tree). |
| `benefits`             | text                     | What the beneficiary receives. |
| `documents_required`   | string[]                 | e.g. `["Aadhaar card", "Land records", "Bank passbook"]`. |
| `application_process`  | text                     | How to apply, step by step. |
| `official_source_url`  | string                   | Authoritative page describing the scheme (gov domain). |
| `apply_url`            | string \| null           | Direct link to the application portal, if one exists. |
| `last_verified_date`   | date \| null             | When a human last confirmed this record against the source. |
| `verification_status`  | enum                     | `verified` \| `needs_review` \| `stale`. Defaults to `needs_review`. |

`created_at` / `updated_at` timestamps are added by Prisma and are not part of
the conceptual model.

### TypeScript shape

```ts
interface Scheme {
  scheme_id: string;
  name: string;
  short_summary: string;
  level: "Central" | "State";
  state: IndianState | null; // non-null iff level === "State"
  category: string[];
  eligibility: Eligibility;
  benefits: string;
  documents_required: string[];
  application_process: string;
  official_source_url: string;
  apply_url: string | null;
  last_verified_date: string | null; // ISO date, YYYY-MM-DD
  verification_status: "verified" | "needs_review" | "stale";
}
```

---

## Eligibility condition tree

`Scheme.eligibility` is a single JSON object with two independent condition
trees:

```ts
interface Eligibility {
  /** Must evaluate true for the user to be eligible at all. */
  hard: ConditionNode;
  /** Only affects ranking/priority. Never excludes a user. May be null. */
  soft: ConditionNode | null;
}
```

- **`hard`** — the gate. If it evaluates to `false`, the scheme is **not**
  shown as a match.
- **`soft`** — the tiebreaker. Used to rank or prioritise schemes the user is
  already eligible for (e.g. "prefer schemes that specifically target this
  user's category"). An unmatched `soft` condition **does not** exclude the
  scheme.

Both use the exact same `ConditionNode` grammar.

### `ConditionNode` grammar

A node is exactly one of three kinds:

```ts
type ConditionNode = GroupNode | NotNode | LeafCondition;

interface GroupNode {
  op: "AND" | "OR";
  children: ConditionNode[]; // 1 or more
}

interface NotNode {
  op: "NOT";
  child: ConditionNode;
}

interface LeafCondition {
  field: UserProfileFieldKey; // one of the field keys in section A
  operator: Operator;
  value: unknown; // shape depends on operator; see table
}

type UserProfileFieldKey =
  | "state"
  | "age"
  | "gender"
  | "annual_family_income"
  | "occupation"
  | "education_level"
  | "category"
  | "support_type_needed"
  // optional / nullable fields
  | "land_holding"
  | "paid_income_tax_last_year"
  | "monthly_pension"
  | "government_employee_grade";
```

Rules:

- Every `LeafCondition.field` **must** be one of the `UserProfile` field keys
  (12 of them). Any other value is invalid data.
- `AND` / `OR` groups take a non-empty `children` array. Nest freely for deeper
  logic.
- `NOT` wraps exactly one `child`.
- An empty `hard` gate should be written as `{ "op": "AND", "children": [] }`,
  which is defined to evaluate `true` (scheme open to everyone). `soft` may be
  `null` instead.

### Operators

| Operator     | Applies to fields | `value` shape | Meaning |
|--------------|-------------------|---------------|---------|
| `equals`     | any               | scalar        | profile value `===` `value` |
| `not_equals` | any               | scalar        | profile value `!==` `value` |
| `in`         | any               | array         | profile value is one of `value[]` |
| `not_in`     | any               | array         | profile value is not in `value[]` |
| `gte`        | numeric (`age`, `annual_family_income`, `monthly_pension`) | number | profile value `>=` `value` |
| `lte`        | numeric (`age`, `annual_family_income`, `monthly_pension`) | number | profile value `<=` `value` |
| `exists`     | any               | *(ignored)*   | profile has a non-null value for `field` |
| `not_exists` | any               | *(ignored)*   | profile has no value for `field` |

The write-time validator narrows "any" by field type: enum fields (incl.
`land_holding`, `government_employee_grade`) allow
`equals`/`not_equals`/`in`/`not_in`/`exists`/`not_exists`; the boolean field
`paid_income_tax_last_year` allows `equals`/`not_equals`/`exists`/`not_exists`
(value must be `true` or `false`); numeric fields (`age`,
`annual_family_income`, `monthly_pension`) allow `gte`/`lte`/`exists`/`not_exists`.

> `exists` / `not_exists` are here for forward compatibility. Every
> `UserProfile` field is currently required, so `exists` is always true today;
> it becomes meaningful if optional profile fields are added later.

### Example

`pm-kisan`-style: Central scheme, farmers only, family income at or below
₹2,00,000, and (as a soft preference) prioritise SC/ST applicants.

```json
{
  "hard": {
    "op": "AND",
    "children": [
      { "field": "occupation", "operator": "equals", "value": "farmer" },
      { "field": "annual_family_income", "operator": "lte", "value": 200000 }
    ]
  },
  "soft": {
    "field": "category",
    "operator": "in",
    "value": ["sc", "st"]
  }
}
```

A state scheme would additionally carry `level: "State"` and
`state: "Maharashtra"` on the `Scheme` record itself (not inside the tree); the
matching engine is expected to apply that state filter before evaluating
`eligibility`.

---

## Enum reference

### IndianState

Stored as the official name with spaces replaced by underscores.

**States (28):** `Andhra_Pradesh`, `Arunachal_Pradesh`, `Assam`, `Bihar`,
`Chhattisgarh`, `Goa`, `Gujarat`, `Haryana`, `Himachal_Pradesh`, `Jharkhand`,
`Karnataka`, `Kerala`, `Madhya_Pradesh`, `Maharashtra`, `Manipur`, `Meghalaya`,
`Mizoram`, `Nagaland`, `Odisha`, `Punjab`, `Rajasthan`, `Sikkim`, `Tamil_Nadu`,
`Telangana`, `Tripura`, `Uttar_Pradesh`, `Uttarakhand`, `West_Bengal`

**Union Territories (8):** `Andaman_and_Nicobar_Islands`, `Chandigarh`,
`Dadra_and_Nagar_Haveli_and_Daman_and_Diu`, `Delhi`, `Jammu_and_Kashmir`,
`Ladakh`, `Lakshadweep`, `Puducherry`

---

## Open items (deferred, not part of scaffolding)

- **`Scheme.state` conditional nullability** — "non-null iff `level = State`" is
  not enforced by the database. Add a `CHECK` constraint (or validate in the
  API layer) when scheme writes are implemented.
- **Leaf `field` validation** — that `LeafCondition.field` is one of the eight
  allowed keys is a documented invariant, not a DB constraint. Enforce it with
  a Zod/JSON-schema validator on write.
- **Operator/field/value type-agreement** — e.g. rejecting `gte` on `gender`.
  Same: a write-time validator's job.
