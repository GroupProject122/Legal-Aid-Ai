/** Text helpers for the Schemes result cards (pure, tested in cardText.test.js). */

export const GROUP_LABELS = {
  likely_eligible: 'Likely eligible',
  might_be_eligible: 'You might be eligible',
  check_with_authority: 'Check with the authority',
  not_eligible: 'Not eligible'
};

/**
 * The one-line benefit summary on a collapsed card: the first sentence of `benefits`, cut at a
 * word boundary with an ellipsis if it is longer than `max` characters.
 */
export function benefitSummary(benefits, max = 110) {
  const text = String(benefits || '').replace(/\s+/g, ' ').trim();
  const first = text.split(/(?<=[.!?])\s+(?=[A-Z0-9₹"(])/)[0] || '';
  if (first.length <= max) return first;
  const cut = first.slice(0, max - 1);
  const atWord = cut.slice(0, cut.lastIndexOf(' ') > max * 0.6 ? cut.lastIndexOf(' ') : cut.length);
  return `${atWord.replace(/[\s,;:.-]+$/, '')}…`;
}
