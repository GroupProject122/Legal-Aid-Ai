/**
 * Dropdown / checkbox option lists for the complaint-drafter intake forms.
 * `value` is exactly what backend/complaint_drafter.py's enums expect;
 * `label` is what the user sees. Same { value, label } shape as
 * schemes/options.js.
 */

// --- Scenario 1: tenancy eviction (Delhi Rent Control Act, 1958) ---
// Matches complaint_drafter.EvictionGround / GROUND_LABEL.
export const EVICTION_GROUNDS = [
  { value: 'arrears', label: 'Non-payment of arrears of rent' },
  { value: 'subletting', label: 'Unauthorized subletting' },
  { value: 'damage', label: 'Substantial damage to the premises' },
  { value: 'bona_fide_requirement', label: "Bona fide personal requirement of the landlord" }
];

// Matches complaint_drafter.ReliefSought.
export const TENANCY_RELIEF_OPTIONS = [
  { value: 'recovery_of_possession', label: 'Recovery of possession' },
  { value: 'arrears_payment', label: 'Payment of arrears due' },
  { value: 'damages', label: 'Damages / compensation' }
];

// --- Scenario 2: consumer defective goods / deficient service (Consumer Protection Act, 2019) ---
// Matches complaint_drafter.DefectOrDeficiencyType / GOODS_TYPE_LABEL.
export const DEFECT_OR_DEFICIENCY_TYPES = [
  { value: 'defective_goods', label: 'Defective goods' },
  { value: 'deficient_service', label: 'Deficient service' },
  { value: 'short_delivery', label: 'Short delivery of goods' },
  { value: 'spurious_goods', label: 'Spurious goods' },
  { value: 'unfair_trade_practice_in_sale', label: 'Unfair trade practice in sale' }
];

// Matches complaint_drafter.GoodsReliefSought.
export const GOODS_RELIEF_OPTIONS = [
  { value: 'refund', label: 'Refund' },
  { value: 'replacement', label: 'Replacement' },
  { value: 'compensation', label: 'Compensation' },
  { value: 'removal_of_defect', label: 'Removal of defect' }
];

/** For the boolean field `prior_complaint_made`. */
export const YES_NO = [
  { value: 'true', label: 'Yes' },
  { value: 'false', label: 'No' }
];

// --- Scenario 3: misleading advertisement / dark patterns (Consumer Protection Act, 2019) ---
// Matches complaint_drafter.PlatformOrMedium / PLATFORM_LABEL.
export const PLATFORM_OR_MEDIUM_OPTIONS = [
  { value: 'print', label: 'Print' },
  { value: 'television', label: 'Television' },
  { value: 'digital_display', label: 'Digital display' },
  { value: 'social_media', label: 'Social media' },
  { value: 'e_commerce_website', label: 'E-commerce website' },
  { value: 'other', label: 'Other' }
];

// Matches complaint_drafter.AdvertisementClaimType / ADS_CLAIM_TYPE_LABEL.
export const ADVERTISEMENT_CLAIM_TYPES = [
  { value: 'false_claim_about_goods', label: 'False claim about goods or service' },
  { value: 'misleading_price_representation', label: 'Misleading price representation' },
  { value: 'dark_pattern_deceptive_design', label: 'Dark pattern / deceptive design' },
  { value: 'false_guarantee_or_warranty', label: 'False guarantee or warranty' },
  { value: 'surrogate_advertisement', label: 'Surrogate advertisement' }
];

// Matches complaint_drafter.AdsReliefSought.
export const ADS_RELIEF_OPTIONS = [
  { value: 'discontinuation_of_practice', label: 'Discontinue the practice' },
  {
    value: 'compensation',
    label: 'Compensation',
    // Advisory only, does not block submission -- the backend has no reliable way to judge
    // "was there real harm" from free text (and deliberately doesn't try to), so this is a
    // hint at the point of choice rather than a validator.
    hint: 'Compensation relief should be supported by a description of actual financial loss.'
  },
  { value: 'corrective_advertisement', label: 'Corrective advertisement' }
];
