# Gemini Domain Router Evaluation

## Overall Results
- Total queries: 50
- Overall accuracy: 94.0%
- Status accuracy: 98.0%
- Domain exact accuracy: 94.0%
- Average domain recall: 98.0%
- Primary-domain accuracy: 98.0%

## Supported Domain Classification
- Single-domain accuracy: 89.3%; primary-domain accuracy: 96.4%

## Multi-Domain Cases
- Exact-match accuracy: 100.0%; average domain recall: 100.0%

## Unclear Cases
- Unclear detection accuracy: 100.0%

## Unsupported Legal Cases
- Unsupported detection accuracy: 100.0%

## Out-of-Scope Cases
- Out-of-scope detection accuracy: 100.0%

## Hinglish Examples
- `seller refund nahi de raha` -> `classified` ['consumer']
- `defective product replace nahi hua` -> `classified` ['consumer']
- `online order damaged nikla aur company help nahi kar rahi` -> `classified` ['consumer']
- `misleading advertisement dekh kar product kharida aur loss ho gaya` -> `classified` ['consumer', 'constitutional_public_authority']
- `app ne dark pattern se mujhe subscription mein phasa diya` -> `classified` ['consumer']
- `direct selling company refund deny kar rahi hai` -> `classified` ['consumer']
- `mera Instagram hack ho gaya` -> `classified` ['cyber']
- `UPI fraud ho gaya aur bank transaction unauthorized hai` -> `classified` ['cyber', 'consumer']
- `social media par meri private information share kar di` -> `classified` ['cyber']
- `intermediary unlawful content remove nahi kar raha` -> `classified` ['cyber']
- `landlord electricity cut kar raha hai` -> `classified` ['tenancy']
- `security deposit return nahi kar raha landlord` -> `classified` ['tenancy']
- `Delhi mein landlord bina notice eviction bol raha hai` -> `classified` ['tenancy']
- `tenant rent pay nahi kar raha` -> `classified` ['tenancy']
- `rent agreement dispute hai` -> `classified` ['tenancy']
- `landlord suddenly rent badha raha hai` -> `classified` ['tenancy']
- `RTI ka reply nahi mila` -> `classified` ['constitutional_public_authority']

## Failure Examples
- `misleading advertisement dekh kar product kharida aur loss ho gaya` expected `classified` ['consumer']; got `classified` ['consumer', 'constitutional_public_authority']
- `UPI fraud ho gaya aur bank transaction unauthorized hai` expected `classified` ['cyber']; got `classified` ['cyber', 'consumer']
- `court order deliberately disobeyed hai` expected `classified` ['constitutional_public_authority']; got `unsupported` []

## Cost And Latency
- Router Gemini calls: 50
- Failed/fallback calls: 0
- Average routing latency: 1587.9 ms

## Recommended Next Step
- Part 8B should add clarification-question generation for `unclear` cases without changing retrieval ranking.
