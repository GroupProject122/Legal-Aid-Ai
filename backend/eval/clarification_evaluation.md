# Adaptive Clarification Evaluation

## Overall Results
- Scenarios: 24
- Clarification-trigger accuracy: 95.8%
- Final status accuracy: 100.0%
- Final domain accuracy: 100.0%
- Overall accuracy: 95.8%

## One-Turn Resolution
- One-turn resolution rate: 90.0%

## Multi-Turn Resolution
- Repeated-question rate: 0.0%
- Stuck safety success rate: 100.0%

## Hinglish Cases
- `mere paise fas gaye` -> questions 1; final `classified` ['consumer', 'cyber']
- `mujhe refund issue hai` -> questions 1; final `classified` ['consumer']
- `paise chale gaye` -> questions 1; final `classified` ['cyber']
- `account problem hai` -> questions 1; final `classified` ['cyber']
- `deposit nahi mil raha` -> questions 1; final `classified` ['tenancy']
- `ghar ka issue hai` -> questions 1; final `classified` ['tenancy']
- `government office problem hai` -> questions 1; final `classified` ['constitutional_public_authority']
- `mujhe help chahiye` -> questions 1; final `classified` ['constitutional_public_authority']
- `mujhe notice mila hai` -> questions 1; final `unsupported` []
- `family matter hai` -> questions 1; final `unsupported` []
- `court matter hai` -> questions 1; final `unsupported` []
- `mujhe kuch puchna hai` -> questions 1; final `out_of_scope` []
- `online paise ka issue hai` -> questions 1; final `classified` ['consumer', 'cyber']
- `landlord trouble kar raha hai` -> questions 1; final `classified` ['tenancy', 'cyber']
- `mera matter hai` -> questions 2; final `unclear` []
- `mere saath galat hua` -> questions 2; final `unclear` []
- `landlord electricity cut kar raha hai` -> questions 0; final `classified` ['tenancy']
- `seller refund nahi de raha defective product ke liye` -> questions 0; final `classified` ['consumer']
- `RTI application ka reply nahi mila` -> questions 0; final `classified` ['constitutional_public_authority']

## Unsupported Resolution
- `mujhe notice mila hai` -> `unsupported`
- `family matter hai` -> `unsupported`
- `court matter hai` -> `unsupported`

## Stuck / Non-Informative Cases
- `mera matter hai` stopped by `stuck_exit`
- `mere saath galat hua` stopped by `unclear`

## Failure Examples
- `company ne galat kiya` expected `classified` ['consumer']; got `classified` ['consumer']

## Cost And Latency
- Router calls: 46
- Gemini clarification calls: 22
- Average clarification latency: 1627.8 ms

## Recommended Next Step
- Part 8C can add conditional jurisdiction questions after a domain is clear.
