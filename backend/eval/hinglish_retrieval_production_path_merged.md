# Hinglish retrieval, production path (pre-rebuild vs rebuilt index)

Method: `rag.retrieve()` on the 11 Hinglish queries in `retrieval_queries.json`, on the raw text and on its `query_normalizer` rewrite. The rewrite was generated once and reused on both indexes, so only the index differs. Hit = an expected primary source among the returned chunks.

| Index | Mode | Doc found | Doc at #1 | Provision found |
|---|---|---:|---:|---:|
| pre-rebuild (2026-09-07, 4,315 chunks) | raw | 10/11 | 9/11 | 1/11 |
| pre-rebuild (2026-09-07, 4,315 chunks) | normalised | 11/11 | 9/11 | 3/11 |
| rebuilt (6,697 chunks, windowed) | raw | 11/11 | 10/11 | 1/11 |
| rebuilt (6,697 chunks, windowed) | normalised | 10/11 | 7/11 | 3/11 |

Normaliser rewrote 7/11 queries.

## Per query (rebuilt index)

| Query | Rewrite | Raw: doc / #1 | Normalised: doc / #1 |
|---|---|---|---|
| `online seller refund nahi de raha` | `online seller refund nahi de raha` | True / True | True / True |
| `misleading advertisement se mera nuksan hua` | `misleading advertisement se mera nuksan hua` | True / True | True / True |
| `consumer complaint kahan file karu` | `consumer complaint kahan file karu` | True / True | True / True |
| `online payment mein cyber fraud hua` | `cyber fraud in online payment` | True / True | True / False |
| `kisi ne mera social media account hack kar diya` | `someone hacked my social media account` | True / False | False / False |
| `online cybercrime kaise report karu` | `how to report online cybercrime` | True / True | True / False |
| `landlord ne bijli kaat di` | `landlord cut off electricity` | True / True | True / True |
| `landlord security deposit wapas nahi kar raha` | `landlord security deposit wapas nahi kar raha` | True / True | True / True |
| `RTI application mein issue hai` | `RTI application issue` | True / True | True / True |
| `free legal aid ke liye eligibility kya hai` | `free legal aid eligibility` | True / True | True / True |
| `mera Instagram hack ho gaya` | `Instagram account hacked` | True / True | True / False |
