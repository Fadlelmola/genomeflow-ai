# Workflow and evaluation
Project upload accepts individual FASTQ files plus one CSV sample sheet per assay or a tar.gz archive containing reads and samplesheet.csv. Required columns are sample and fastq_1. Include fastq_2 for paired reads. Additional project metadata accepts CSV or JSON. The single-sample workflow reads a local file path. SQLite stores project results locally.

QC review accepts an exported GenomeFlow CSV. Local tools report read totals, pooled Q30 percentage or the count of samples meeting a supplied Q30 cutoff. The cutoff evaluates one raw-read criterion. Assessment of overall sample quality requires assay-specific measures.

To enable optional API routing, configure OPENAI_API_KEY and OPENAI_MODEL in the local launch environment before starting Streamlit. Only the typed question is sent to the API. Keep identifying details out of questions. Local tools work without credentials.

The Day 2 synthetic run covered 30 samples and 3,132,632 reads. The Day 4 tests simulated provider responses. Live routing accuracy and performance above 10,000 samples still need validation.
