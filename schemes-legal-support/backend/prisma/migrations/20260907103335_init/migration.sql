-- CreateEnum
CREATE TYPE "indian_state" AS ENUM ('Andhra_Pradesh', 'Arunachal_Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal_Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya_Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil_Nadu', 'Telangana', 'Tripura', 'Uttar_Pradesh', 'Uttarakhand', 'West_Bengal', 'Andaman_and_Nicobar_Islands', 'Chandigarh', 'Dadra_and_Nagar_Haveli_and_Daman_and_Diu', 'Delhi', 'Jammu_and_Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry');

-- CreateEnum
CREATE TYPE "gender" AS ENUM ('male', 'female', 'other');

-- CreateEnum
CREATE TYPE "occupation" AS ENUM ('farmer', 'student', 'unemployed', 'salaried', 'self_employed', 'other');

-- CreateEnum
CREATE TYPE "education_level" AS ENUM ('below_10th', '10th_pass', '12th_pass', 'graduate', 'postgraduate', 'other');

-- CreateEnum
CREATE TYPE "social_category" AS ENUM ('general', 'obc', 'sc', 'st', 'other');

-- CreateEnum
CREATE TYPE "support_type" AS ENUM ('financial_aid', 'education', 'healthcare', 'housing', 'employment', 'agriculture', 'business', 'other');

-- CreateEnum
CREATE TYPE "scheme_level" AS ENUM ('Central', 'State');

-- CreateEnum
CREATE TYPE "verification_status" AS ENUM ('verified', 'needs_review', 'stale');

-- CreateTable
CREATE TABLE "user_profiles" (
    "id" TEXT NOT NULL,
    "state" "indian_state" NOT NULL,
    "age" INTEGER NOT NULL,
    "gender" "gender" NOT NULL,
    "annual_family_income" INTEGER NOT NULL,
    "occupation" "occupation" NOT NULL,
    "education_level" "education_level" NOT NULL,
    "category" "social_category" NOT NULL,
    "support_type_needed" "support_type" NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "user_profiles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "schemes" (
    "id" TEXT NOT NULL,
    "scheme_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "short_summary" TEXT NOT NULL,
    "level" "scheme_level" NOT NULL,
    "state" "indian_state",
    "category" TEXT[],
    "eligibility" JSONB NOT NULL,
    "benefits" TEXT NOT NULL,
    "documents_required" TEXT[],
    "application_process" TEXT NOT NULL,
    "official_source_url" TEXT NOT NULL,
    "apply_url" TEXT,
    "last_verified_date" DATE,
    "verification_status" "verification_status" NOT NULL DEFAULT 'needs_review',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "schemes_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "schemes_scheme_id_key" ON "schemes"("scheme_id");

-- CreateIndex
CREATE INDEX "schemes_level_idx" ON "schemes"("level");

-- CreateIndex
CREATE INDEX "schemes_state_idx" ON "schemes"("state");

-- CreateIndex
CREATE INDEX "schemes_verification_status_idx" ON "schemes"("verification_status");
