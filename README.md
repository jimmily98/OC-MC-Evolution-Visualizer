# OC to MC development

This workspace contains a small parser for the Baxter-Sagart Old Chinese PDF and the extracted MC mapping tables.

## Project Layout

- `ocmc/` contains the parser, parsing helpers, and linkage generation code.
- `data/` contains the extracted records and generated linkage summaries.
- `dash_app.py` is the step-4 dashboard with clickable Sankey drilldown.

## GitHub Ready

This workspace now includes a `.gitignore` for Python, virtual environment, and editor artifacts.

To turn this workspace into a local git repository, run:

```bash
git init
git add .
git commit -m "Initial OC to MC project"
```

After that, create an empty repository on GitHub and add it as a remote:

```bash
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main
```

## Run


To launch the dashboard (Dash, with flow-click drilldown):

```bash
python dash_app.py
```

Legacy Streamlit dashboard:

```bash
streamlit run app.py
```

## Notes

The Dash dashboard is the recommended step-4 interface because it supports direct flow-click drilldown from each Sankey link into the correspondence table.