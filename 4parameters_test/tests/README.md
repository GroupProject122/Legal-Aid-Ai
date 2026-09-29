# Answer-quality metrics

Tools for measuring the quality of Legal Aid AI's answers on the external test sets in
`../externaltestset/`. Installed so far: **ROUGE** and **BERTScore**. AlignScore and
ParaScore will be added here later.

| Metric | What it measures | Needs a reference answer? | Test set |
|---|---|---|---|
| **ROUGE** (`rouge-score`) | Word overlap between the app's answer and a reference answer | Yes | Set 1 (official Q&A) |
| **BERTScore** (`bert-score`) | Meaning overlap between the app's answer and a reference answer, using a language model, so paraphrases still score well | Yes | Set 1 (official Q&A) |
| AlignScore *(to add)* | Whether every claim in the answer is supported by the sources the app retrieved | No | Set 2 (real phrasing) |
| ParaScore *(to add)* | Whether the app's rewritten version of a question keeps its meaning | No | Set 2 (real phrasing) |

**Known weakness of ROUGE and BERTScore:** both reward similar wording, so they can score
"you **may not** claim a refund" highly against "you **may** claim a refund". The check
script includes this case on purpose. That is why they are reported alongside AlignScore
and a small hand review, not on their own.

## What is where

| Path | What it is | In git? |
|---|---|---|
| `.venv/` | Separate Python environment with the metric packages | No (large, recreate below) |
| `models/` | BERTScore's model, `roberta-large` (~1.4 GB), downloaded on first run | No (large, downloads automatically) |
| `requirements-metrics.txt` | The packages and versions to install | Yes |
| `check_metrics.py` | Checks the installation by scoring sample answer pairs | Yes |
| `make_set1_report.py` | Builds `../externaltestset/set 1/Set1_Official_QA_Test_Set.pdf` from the Set 1 test file (rerun after changing it) | Yes |
| `results/` | Saved scores (`metrics_check.json` from the check) | Yes |

The environment is kept separate from `backend/` on purpose: the metric packages can
change shared library versions, which could break the app's own search model.

## Set up (once per computer)

Run these in a terminal from this folder (`4parameters_test/tests`). No GPU is needed.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-metrics.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-metrics.txt
```

## Run

Switch the environment on (`.\.venv\Scripts\Activate.ps1` on Windows,
`source .venv/bin/activate` on macOS/Linux), then:

```bash
python check_metrics.py
```

The first run downloads the BERTScore model into `models/`, which takes several minutes.
Later runs reuse it and take well under a minute. Results are printed and saved to
`results/metrics_check.json`.

When you finish, `deactivate` switches the environment off.

## Versions used

Python 3.13.7 · torch 2.14.0 (CPU) · transformers 5.17.0 · rouge-score 0.1.2 ·
bert-score 0.3.13 · BERTScore model `roberta-large`, rescaled with baseline.
