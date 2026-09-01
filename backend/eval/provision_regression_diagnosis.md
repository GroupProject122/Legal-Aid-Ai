# Provision Regression Diagnosis

## Summary
- Provision-labelled queries: 11
- Part 7B Hit@5 count: 10
- Part 7C Hit@5 count: 10
- New regression count: 0
- Pre-existing provision misses: 1
- Production code changed by this diagnosis: True

## Provision Query Comparison
| Query | Expected Provision(s) | 7B Rank | 7B Hit@5 | 7C Rank | 7C Hit@5 |
|---|---:|---:|---:|---:|---:|
| online seller refusing refund | 39, 83, 86 | 1 | True | 1 | True |
| defective product and seller not replacing it | 39, 83, 86 | 1 | True | 1 | True |
| limitation period for consumer complaint | 69 | 1 | True | 1 | True |
| can consumer commission order repair or replacement | 39 | 1 | True | 1 | True |
| unauthorized access to computer account | 43, 66 | not in Top 10 | False | not in Top 10 | False |
| landlord cut electricity | 45 | 2 | True | 2 | True |
| landlord wants to evict me without proper process | 14 | 1 | True | 1 | True |
| essential supply stopped by landlord | 45 | 1 | True | 1 | True |
| right to equality | 14 | 1 | True | 1 | True |
| freedom of speech restriction | 19 | 1 | True | 1 | True |
| right to life and personal liberty | 21 | 1 | True | 1 | True |

## New Regression Queries
- None.

## Pre-Existing Provision Misses
- `unauthorized access to computer account` expected ['43', '66']; 7B rank not in Top 10, 7C rank not in Top 10.

## Recommendation
- The Part 7C provision regression has been removed by a narrow public-authority query-expansion fix. One pre-existing cyber provision miss remains because the expected IT Act provisions are absent from the raw Top 10 candidate pool. Do not broadly retune retrieval for that in Part 7D; handle it later with focused cyber provision evaluation if needed.
