# Datathon Final Report

This folder contains the business-first LaTeX report draft and a standalone model-methodology report.

## Build

Recommended:

```powershell
cd report
latexmk -pdf main.tex
```

To build the model-focused report:

```powershell
cd report
latexmk -pdf model_report.tex
```

If the official NeurIPS style file is available, place `neurips_2025.sty` in this folder and rebuild. The report has a fallback `article` layout so it can compile without the style file.

## Framing

Main story:

> Revenue follows seasonal demand; COGS reflects margin and promotion regime.

The main text is written as a business forecasting analysis. It frames the solution around provided historical datasets, calendar structure, demand seasonality, and margin-regime behavior.

## Final Candidate

Final clean report candidate:

```text
dataset/submission_cleanv19_v17_ratio_monthsmooth_h2_recenteven_a150.csv
MAE: 667139.04897
```

## Source Documents

Official requirement extract:

```text
requirements/extracted_reqs_updated.txt
```

Friend analyst PDF to convert before final polishing:

```powershell
markitdown "docs\datathon_2026_analyst.pdf" -o "docs\datathon_2026_analyst.md"
```

Use claims from that PDF only after verifying them against provided data or clean logs.
