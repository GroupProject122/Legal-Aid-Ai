# Fact Sufficiency Evaluation

## Overall Results
- Scenarios: 39
- Sufficiency decision accuracy: 97.4%
- Final sufficiency accuracy: 97.4%
- Overall accuracy: 97.4%
- Unnecessary-question rate: 2.6%
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
- `phishing link se paise chale gaye, OTP 123456 tha`
- `court order deliberately disobeyed hai`
- `someone used my identity online`
- `landlord wants to evict me without proper process`
- `dark pattern forced me to subscribe`
- `Who is a consumer?`
- `Who is a not a consumer?`
- `What is an unfair contract?`
- `Is there any fee for mediation?`
- `consumer kaun hota hai?`
- `How can I file the complaints about other cybercrimes?`
- `What type of information would be considered as evidence while filing my complaint related to cybercrime?`
- `What is the fee for filing an RTI application?`

## Queries Correctly Clarified
- `consumer complaint karni hai` -> `What happened with the product or service?`
- `consumer issue hai` -> `What happened with the product or service?`
- `mera cyber issue hai` -> `What happened — account hacking, payment fraud, identity misuse, or something else?`
- `online problem hai` -> `What happened — account hacking, payment fraud, identity misuse, or something else?`
- `landlord dispute hai` -> `What is the dispute about — eviction, rent, deposit, or power/water supply?`
- `rent matter hai` -> `What is the dispute about — eviction, rent, deposit, or power/water supply?`
- `government authority ke against issue hai` -> `What did the public authority do or refuse to do?`
- `rights issue hai` -> `What did the public authority do or refuse to do?`
- `online payment issue hai` -> `What happened with the product or service?`
- `consumer issue hai` -> `What happened with the product or service?`
- `mera cyber issue hai` -> `What happened — account hacking, payment fraud, identity misuse, or something else?`
- `public authority problem hai` -> `What did the public authority do or refuse to do?`
- `consumer complaint karni hai` -> `What happened with the product or service?`
- `What should I do about my landlord?` -> `What is the dispute about — eviction, rent, deposit, or power/water supply?`
- `I paid 5000 rupees for a course, what are my rights?` -> `What happened with the product or service?`
- `my bank account was emptied, can I get it back?` -> `What happened — account hacking, payment fraud, identity misuse, or something else?`
- `mujhe kya karna chahiye?` -> `What happened with the product or service?`

## Unnecessary Clarification Cases
- `Instagram seller took payment and blocked me`

## One-Turn Resolution
- One-turn resolution rate: 88.2%

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
- `consumer kaun hota hai?` -> `sufficient`
- `consumer complaint karni hai` -> `sufficient`
- `mujhe kya karna chahiye?` -> `sufficient`

## Stuck Cases
- `consumer issue hai` stopped by `stuck_exit`
- `mera cyber issue hai` stopped by `insufficient`

## Failure Examples
- `Instagram seller took payment and blocked me` expected first clarification `False` and final `sufficient`; got first clarification `True` and final `insufficient`

## Cost And Latency
- Gemini fact-sufficiency calls: 0
- Average fact-check latency: None ms

## Recommendation
- Proceed to the next conversation layer only after reviewing any remaining unnecessary or missing clarification cases.
