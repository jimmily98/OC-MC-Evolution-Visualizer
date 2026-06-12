# OC to MC development

This project is a computational linguistics tool designed to map the phonological transition from Old Chinese (OC) to Middle Chinese (MC). By leveraging the Baxter-Sagart OC reconstruction(2014), this project traces how ancient phonemes evolved into traditional medieval categories.


## Data Source

The primary data source is the [Baxter-Sagart Old Chinese reconstruction, version 1.1](https://sites.lsa.umich.edu/ocbaxtersagart/wp-content/uploads/sites/1415/2025/03/BaxterSagartOCbyGSR2014-09-20.pdf). This dataset contains ~5,000 lexical entries including:

- OC Forms: Parsed into an Onset (Minor Syllable + Root Initial) and a Rhyme (Medial + Nucleus + Coda).

- MC Forms: Conventional ASCII transcriptions mapped to traditional Initial Groups and Rhyme Groups based on the **廣韻** system. Description of this MC transcription system is given in Section 2.1.2 of [Old Chinese: A NEW RECONSTRUCTION](https://www.researchgate.net/publication/317400587_Old_Chinese_A_New_Reconstruction).


## Project Layout

- `ocmc/` contains the parser, parsing helpers, and linkage generation code.
- `data/` contains the extracted records and generated linkage summaries.
- `dash_app.py` is the visualization dashboard.

## Installation

To copy this project to your local machine and set it up, run:

```
# Clone the repository
git clone <your-github-repo-url>
cd <repo-folder-name>

# Install required dependencies
pip install -r requirements.txt
```

## Run

To launch the Dash dashboard (supports direct drilldown from Sankey links to correspondence tables):

```
python dash_app.py
```

## Notes

The Dash dashboard is the recommended interface because it supports direct flow-click drilldown from each Sankey link into the correspondence table.