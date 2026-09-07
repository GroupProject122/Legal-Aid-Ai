-- CreateEnum
CREATE TYPE "land_holding" AS ENUM ('none', 'individual', 'institutional');

-- CreateEnum
CREATE TYPE "government_employee_grade" AS ENUM ('not_applicable', 'group_a_b_c', 'group_d_mts');

-- AlterTable
ALTER TABLE "user_profiles" ADD COLUMN     "government_employee_grade" "government_employee_grade",
ADD COLUMN     "land_holding" "land_holding",
ADD COLUMN     "monthly_pension" INTEGER,
ADD COLUMN     "paid_income_tax_last_year" BOOLEAN;
