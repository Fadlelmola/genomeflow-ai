# GenomeFlow: AI Multi-Agent System
A research prototype for calculating raw-read quality metrics from FASTQ files and reviewing results by project, assay and sample.

## Features
- Run RNA-seq, exome or whole-genome sequencing alone or in one project.
- Match reads to sample-sheet entries, calculate read and base counts, Q30 percentage, GC percentage and N count, and export a CSV.
- Review results locally or use an optional OpenAI Responses API router to select a local calculation.

## Getting started on Windows
Install Python 3.12. Extract the package or clone the published repository. Open Command Prompt in the folder containing app.py.
```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## First run
Select Project upload. Enter a unique project ID and confirm research use for the synthetic example. Under RNA-seq select both files in examples together. Click Analyze project. Expect 2 reads, 8 bases, 75% Q30, 50% GC and 2 N bases. Download the CSV and open QC review to explore the result.

## Testing
From the repository root:
```sh
python -m compileall -q app.py src tests
python -m unittest discover -s tests -v
```
The offline suite covers sample-sheet matching, the synthetic FASTQ calculation, routing and session caching with a simulated provider, unsupported questions, malformed responses, timeout and missing credentials. CI uses these commands on pushes to main and pull requests.

## Documentation
[Workflow and evaluation](docs/workflow.md) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)

## Demo: consent and governance before QC
In Project upload or Single sample, select Synthetic and Synthetic origin confirmed. Choose Approved for local research processing. Leave the identifiers field unresolved for a blocked run, then choose None confirmed and submit again. The app displays the Consent Agent decision, then the Data Governance Agent decision, before the QC Agent processes any reads. Human or mixed datasets are outside this demo. These rules use operator declarations. They do not inspect consent documents or detect identifiers automatically.
