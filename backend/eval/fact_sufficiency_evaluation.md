# Fact Sufficiency Evaluation

## Overall Results
- Scenarios: 26
- Sufficiency decision accuracy: 100.0%
- Final sufficiency accuracy: 100.0%
- Overall accuracy: 100.0%
- Unnecessary-question rate: 0.0%
- Missing-question rate: 0.0%

## Queries Correctly Allowed Through
- `seller refusing refund for defective product`
- `online product damaged deliver hua aur seller replace nahi kar raha`
- `my Instagram account was hacked`
- `phishing link se paise chale gaye`
- `landlord cut electricity`
- `landlord security deposit return nahi kar raha`
- `RTI application ka reply nahi mila`
- `I want free legal aid`
- `Instagram seller took payment and blocked me`
- `phishing link se paise chale gaye, OTP 123456 tha`
- `court order deliberately disobeyed hai`
- `someone used my identity online`
- `landlord wants to evict me without proper process`
- `dark pattern forced me to subscribe`

## Queries Correctly Clarified
- `consumer complaint karni hai` -> `What product or service did you purchase, and what specific issue did you face with the seller or service provider?`
- `consumer issue hai` -> `What product or service did you purchase, and what issue did you face with the seller or provider?`
- `mera cyber issue hai` -> `Could you briefly describe what happened, such as whether this involves unauthorized transactions, hacking, or phishing?`
- `online problem hai` -> `Could you please specify what happened online, such as whether it was unauthorized access, payment fraud, phishing, or another issue?`
- `landlord dispute hai` -> `Could you briefly describe what the dispute with your landlord is about, such as issues related to rent, eviction, or deposit?`
- `rent matter hai` -> `Could you please specify what the rent issue is about, such as a rent increase, eviction, or unpaid rent?`
- `government authority ke against issue hai` -> `Could you briefly specify what action or decision by the government authority led to this issue?`
- `rights issue hai` -> `Could you briefly describe the specific action or authority involved in the rights issue?`
- `online payment issue hai` -> `Could you briefly describe what went wrong during the online payment, such as a failed transaction, unauthorized deduction, or a fraud incident?`
- `consumer issue hai` -> `What product or service was purchased, and what specific issue occurred with the seller or provider?`
- `mera cyber issue hai` -> `Could you briefly describe what happened, such as whether it involves online fraud, unauthorized access, or social media hacking?`
- `public authority problem hai` -> `Could you briefly describe the specific action or inaction by the public authority that led to this issue?`

## Unnecessary Clarification Cases
- None.

## One-Turn Resolution
- One-turn resolution rate: 83.3%

## Hinglish Cases
- `online product damaged deliver hua aur seller replace nahi kar raha` -> `sufficient`
- `consumer complaint karni hai` -> `sufficient`
- `consumer issue hai` -> `sufficient`
- `phishing link se paise chale gaye` -> `sufficient`
- `mera cyber issue hai` -> `sufficient`
- `online problem hai` -> `sufficient`
- `landlord security deposit return nahi kar raha` -> `sufficient`
- `landlord dispute hai` -> `sufficient`
- `rent matter hai` -> `sufficient`
- `RTI application ka reply nahi mila` -> `sufficient`
- `government authority ke against issue hai` -> `sufficient`
- `rights issue hai` -> `sufficient`
- `online payment issue hai` -> `sufficient`
- `consumer issue hai` -> `insufficient`
- `mera cyber issue hai` -> `insufficient`
- `phishing link se paise chale gaye, OTP 123456 tha` -> `sufficient`
- `court order deliberately disobeyed hai` -> `sufficient`
- `public authority problem hai` -> `sufficient`

## Stuck Cases
- `consumer issue hai` stopped by `stuck_exit`
- `mera cyber issue hai` stopped by `insufficient`

## Failure Examples
- No failures under the current labels.

## Cost And Latency
- Gemini fact-sufficiency calls: 16
- Average fact-check latency: 1593.3 ms

## Recommendation
- Proceed to the next conversation layer only after reviewing any remaining unnecessary or missing clarification cases.
