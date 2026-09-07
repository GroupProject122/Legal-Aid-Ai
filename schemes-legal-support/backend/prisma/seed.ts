/**
 * Seed data: 6 hand-authored Indian government schemes for local testing.
 *
 * These are written from general public knowledge of the schemes to exercise
 * the matching engine (AND / OR / NOT / hard+soft / missing-field cases). They
 * are NOT transcribed from official notifications, so every record is marked
 * `verification_status: "needs_review"`. `official_source_url` points at the
 * real portal but the structured eligibility is illustrative.
 *
 * Run with:  npm run prisma:seed   (wired via package.json "prisma".seed)
 */
import { PrismaClient, Prisma } from "@prisma/client";

import type { Eligibility } from "../src/matching/types";

// --- eligibility trees ------------------------------------------------------

/** Simple AND: full-time farmer, household income within the small-farmer cap. */
const pmKisan: Eligibility = {
  hard: {
    op: "AND",
    children: [
      { field: "occupation", operator: "equals", value: "farmer" },
      { field: "annual_family_income", operator: "lte", value: 200_000 },
    ],
  },
  soft: null,
};

/** State scheme with an OR branch: SC/ST/OBC *or* income below the ceiling. */
const mhPostMatric: Eligibility = {
  hard: {
    op: "AND",
    children: [
      { field: "state", operator: "equals", value: "Maharashtra" },
      {
        field: "education_level",
        operator: "in",
        value: ["12th_pass", "graduate", "postgraduate"],
      },
      {
        op: "OR",
        children: [
          { field: "category", operator: "in", value: ["sc", "st", "obc"] },
          { field: "annual_family_income", operator: "lte", value: 800_000 },
        ],
      },
    ],
  },
  // Soft: prioritise the groups the scheme most targets.
  soft: { field: "category", operator: "in", value: ["sc", "st"] },
};

/** NOT: housing support for low-income households, excluding salaried earners. */
const pmayGramin: Eligibility = {
  hard: {
    op: "AND",
    children: [
      { field: "support_type_needed", operator: "equals", value: "housing" },
      { field: "annual_family_income", operator: "lte", value: 300_000 },
      {
        op: "NOT",
        child: { field: "occupation", operator: "equals", value: "salaried" },
      },
    ],
  },
  soft: null,
};

/** Hard AND + soft OR: skilling for 15-45 year olds not in regular salaried work. */
const pmkvy: Eligibility = {
  hard: {
    op: "AND",
    children: [
      { field: "age", operator: "gte", value: 15 },
      { field: "age", operator: "lte", value: 45 },
      {
        field: "occupation",
        operator: "in",
        value: ["unemployed", "student", "self_employed"],
      },
    ],
  },
  soft: {
    op: "OR",
    children: [
      { field: "category", operator: "in", value: ["sc", "st", "obc"] },
      { field: "annual_family_income", operator: "lte", value: 250_000 },
      { field: "education_level", operator: "in", value: ["below_10th", "10th_pass"] },
    ],
  },
};

/** Single condition on `gender` — a field the intake form often leaves blank,
 *  so an incomplete profile lands this scheme in `possibly_eligible`. */
const mahilaSamman: Eligibility = {
  hard: { field: "gender", operator: "equals", value: "female" },
  soft: null,
};

/**
 * PM-KISAN v2 — exercises the 4 optional fields added after converting the real
 * scheme: individual land-holding farmers, excluding income-tax payers and
 * Group A/B/C government staff, and pensioners drawing >= INR 10,000/month
 * (Group D / MTS are exempt from both the employment and the pension bar).
 * Provided verbatim by the reviewer.
 */
const pmKisanV2: Eligibility = {
  hard: {
    op: "AND",
    children: [
      { field: "land_holding", operator: "equals", value: "individual" },
      {
        op: "NOT",
        child: {
          field: "paid_income_tax_last_year",
          operator: "equals",
          value: true,
        },
      },
      {
        op: "OR",
        children: [
          {
            field: "government_employee_grade",
            operator: "equals",
            value: "not_applicable",
          },
          {
            field: "government_employee_grade",
            operator: "equals",
            value: "group_d_mts",
          },
        ],
      },
      {
        op: "OR",
        children: [
          { field: "monthly_pension", operator: "not_exists", value: null },
          { field: "monthly_pension", operator: "lte", value: 9999 },
          {
            field: "government_employee_grade",
            operator: "equals",
            value: "group_d_mts",
          },
        ],
      },
    ],
  },
  soft: null,
};

// --- scheme records ------------------------------------------------------

export const seedSchemes: Prisma.SchemeCreateInput[] = [
  {
    schemeId: "pm-kisan",
    name: "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
    shortSummary:
      "Income support of ₹6,000 a year to land-holding farmer families, paid in three instalments.",
    level: "Central",
    category: ["agriculture", "income-support"],
    eligibility: pmKisan as unknown as Prisma.InputJsonValue,
    benefits:
      "₹6,000 per year transferred directly to the beneficiary's bank account in three equal instalments of ₹2,000.",
    documentsRequired: [
      "Aadhaar card",
      "Land ownership records (khatauni / 7-12 extract)",
      "Bank account passbook",
      "Citizenship certificate",
    ],
    applicationProcess:
      "Register at pmkisan.gov.in or through the nearest Common Service Centre (CSC). Provide Aadhaar, land records and bank details; the state agriculture department verifies land holding before the first instalment.",
    officialSourceUrl: "https://pmkisan.gov.in",
    applyUrl: "https://pmkisan.gov.in/RegistrationFormNew.aspx",
    verificationStatus: "needs_review",
  },
  {
    schemeId: "mh-post-matric-scholarship",
    name: "Maharashtra Post-Matric Scholarship",
    shortSummary:
      "Tuition, exam-fee and maintenance support for post-matric students in Maharashtra from reserved categories or low-income families.",
    level: "State",
    state: "Maharashtra",
    category: ["education", "scholarship"],
    eligibility: mhPostMatric as unknown as Prisma.InputJsonValue,
    benefits:
      "Full reimbursement of tuition and examination fees plus a monthly maintenance allowance of ₹700–₹1,200 depending on course and place of study.",
    documentsRequired: [
      "Domicile certificate of Maharashtra",
      "Caste / category certificate (if claiming reserved-category eligibility)",
      "Income certificate (Tahsildar)",
      "Previous year marksheet",
      "Aadhaar-linked bank account details",
    ],
    applicationProcess:
      "Apply online each academic year on the MahaDBT portal (mahadbt.maharashtra.gov.in). The institute verifies enrolment, then the department sanctions payment to the student's Aadhaar-linked account.",
    officialSourceUrl: "https://mahadbt.maharashtra.gov.in",
    applyUrl: "https://mahadbt.maharashtra.gov.in/Login/Login",
    verificationStatus: "needs_review",
  },
  {
    schemeId: "pmay-gramin",
    name: "Pradhan Mantri Awas Yojana – Gramin (PMAY-G)",
    shortSummary:
      "Financial assistance to build a pucca house for rural households without adequate shelter.",
    level: "Central",
    category: ["housing", "rural-development"],
    eligibility: pmayGramin as unknown as Prisma.InputJsonValue,
    benefits:
      "Construction assistance of ₹1.20 lakh in plain areas (₹1.30 lakh in hilly/difficult areas), 90–95 days of unskilled wage labour under MGNREGA, and a toilet through Swachh Bharat Mission–Gramin.",
    documentsRequired: [
      "Aadhaar card and consent for use",
      "MGNREGA job card",
      "Bank account details",
      "Swachh Bharat Mission (SBM-G) registration number",
      "SECC 2011 / Awaas+ verification",
    ],
    applicationProcess:
      "Beneficiaries are drawn from the SECC 2011 / Awaas+ list and validated by the Gram Sabha. The block office registers the household on the AwaasSoft portal; funds are released in instalments tied to construction milestones verified by geo-tagged photographs.",
    officialSourceUrl: "https://pmayg.nic.in",
    applyUrl: null,
    verificationStatus: "needs_review",
  },
  {
    schemeId: "pmkvy-4",
    name: "Pradhan Mantri Kaushal Vikas Yojana 4.0 (PMKVY)",
    shortSummary:
      "Free short-term skill training and certification for youth who are not in regular salaried employment.",
    level: "Central",
    category: ["employment", "skill-development"],
    eligibility: pmkvy as unknown as Prisma.InputJsonValue,
    benefits:
      "Free NSQF-aligned short-term training (200–600 hours), a government-recognised skill certificate, assessment, and one-time placement/travel support. Recognition of Prior Learning available for existing workers.",
    documentsRequired: [
      "Aadhaar card",
      "Bank account passbook",
      "Educational qualification certificate (if any)",
    ],
    applicationProcess:
      "Enrol at a PMKVY training centre or via the Skill India Digital portal, choose a job role, complete training and third-party assessment, and receive the certificate and any placement support.",
    officialSourceUrl: "https://www.pmkvyofficial.org",
    applyUrl: "https://www.skillindiadigital.gov.in",
    verificationStatus: "needs_review",
  },
  {
    schemeId: "mahila-samman-savings",
    name: "Mahila Samman Savings Certificate",
    shortSummary:
      "A two-year fixed-rate small-savings deposit scheme available exclusively to women and girls.",
    level: "Central",
    category: ["financial-inclusion", "women"],
    eligibility: mahilaSamman as unknown as Prisma.InputJsonValue,
    benefits:
      "Deposits of up to ₹2,00,000 for a two-year term at a fixed 7.5% annual interest, compounded quarterly, with a partial-withdrawal facility of up to 40% after one year.",
    documentsRequired: [
      "Aadhaar card",
      "PAN card",
      "Account opening form (Form-1)",
      "Passport-size photograph",
    ],
    applicationProcess:
      "Open the certificate at any post office or authorised bank before the scheme window closes, by submitting Form-1 with KYC documents and the deposit amount.",
    officialSourceUrl: "https://www.indiapost.gov.in",
    applyUrl: null,
    verificationStatus: "needs_review",
  },
  {
    schemeId: "pm-kisan-v2",
    name: "PM-KISAN Samman Nidhi",
    shortSummary:
      "₹6,000/year income support for individual land-holding farmers, excluding income-tax payers and higher-grade government staff.",
    level: "Central",
    category: ["agriculture", "income-support"],
    eligibility: pmKisanV2 as unknown as Prisma.InputJsonValue,
    benefits:
      "₹6,000/year direct income support in 3 installments of ₹2,000 each, via DBT to Aadhaar-linked bank account.",
    documentsRequired: [
      "Aadhaar card",
      "Land ownership records",
      "Bank account passbook (Aadhaar-linked)",
    ],
    applicationProcess:
      "Register online at pmkisan.gov.in or visit the nearest Common Service Centre. Note: eligibility also depends on your family members' income-tax and government-employment status — this tool checks your individual profile only; verify family-level exclusions on the official portal.",
    officialSourceUrl: "https://pmkisan.gov.in",
    applyUrl: "https://pmkisan.gov.in",
    verificationStatus: "needs_review",
  },
];

// --- runner ------------------------------------------------------------

export async function seed(prisma: PrismaClient): Promise<void> {
  for (const scheme of seedSchemes) {
    await prisma.scheme.upsert({
      where: { schemeId: scheme.schemeId },
      create: scheme,
      update: scheme,
    });
  }
}

async function main(): Promise<void> {
  const prisma = new PrismaClient();
  try {
    await seed(prisma);
    console.log(`Seeded ${seedSchemes.length} schemes.`);
  } finally {
    await prisma.$disconnect();
  }
}

// Only run when invoked directly (`prisma db seed` / `npm run prisma:seed`),
// not when imported by tests.
if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
