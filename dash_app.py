from __future__ import annotations

from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlencode
import json

from dash import Dash, Input, Output, State, dash_table, dcc, html, no_update
import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parent
DEFAULT_LINKAGE_PATH = ROOT / "data" / "oc_mc_linkages.json"
DEFAULT_RECORDS_PATH = ROOT / "data" / "baxter_sagart_records.oc_parsed.ndjson"


def load_summary(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def get_linkage(summary: dict[str, object], source_field: str, target_field: str) -> dict[str, object]:
    for linkage in summary["linkages"]:
        if linkage["source_field"] == source_field and linkage["target_field"] == target_field:
            return linkage
    raise KeyError(f"{source_field} -> {target_field}")


def filter_links(links: list[dict[str, object]], hide_at_most: int | None) -> list[dict[str, object]]:
    filtered: list[dict[str, object]] = []
    for link in links:
        count = int(link["count"])
        if hide_at_most is not None and count <= hide_at_most:
            continue
        filtered.append({"source": str(link["source"]), "target": str(link["target"]), "count": count})

    filtered.sort(key=lambda item: (-item["count"], item["source"], item["target"]))
    return filtered


def build_sankey(links: list[dict[str, object]], source_field: str, target_field: str) -> go.Figure:
    source_totals: Counter[str] = Counter()
    target_totals: Counter[str] = Counter()
    for link in links:
        count = int(link["count"])
        source_totals[str(link["source"])] += count
        target_totals[str(link["target"])] += count

    source_nodes = [source for source, _ in source_totals.most_common()]
    target_nodes = [target for target, _ in target_totals.most_common()]
    labels = source_nodes + target_nodes
    indices = {label: index for index, label in enumerate(labels)}

    link_sources = [indices[str(link["source"])] for link in links]
    link_targets = [indices[str(link["target"])] for link in links]
    link_values = [int(link["count"]) for link in links]
    link_customdata = [f"{link['source']}|||{link['target']}" for link in links]

    source_color = "#1f6f78"
    target_color = "#c97b2c"
    node_colors = [source_color] * len(source_nodes) + [target_color] * len(target_nodes)
    link_color = "rgba(31, 111, 120, 0.22)"

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=16,
                    thickness=18,
                    line=dict(color="rgba(0, 0, 0, 0.14)", width=0.5),
                    label=labels,
                    color=node_colors,
                ),
                link=dict(
                    source=link_sources,
                    target=link_targets,
                    value=link_values,
                    customdata=link_customdata,
                    hovertemplate="%{source.label} → %{target.label}<br>count=%{value}<extra></extra>",
                    color=link_color,
                ),
            )
        ]
    )
    fig.update_layout(
        title=f"{source_field} to {target_field} flow",
        font=dict(size=13, family="Arial, sans-serif", color="#1c2733"),
        height=max(720, 22 * len(labels)),
        margin=dict(l=20, r=20, t=70, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def parse_threshold(value: str) -> int | None:
    if value == "all":
        return None
    return int(value)


def build_detail_rows(
    records: list[dict[str, object]],
    source_field: str,
    target_field: str,
    source: str,
    target: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        if str(record.get(source_field, "")).strip() != source:
            continue
        if str(record.get(target_field, "")).strip() != target:
            continue
        rows.append(
            {
                "index": len(rows) + 1,
                "character": record.get("character", ""),
                "Old Chinese Reconstruction": f"{record.get('oc_form_raw', '')} ({record.get('oc_form_clean', '')})",
                "Middle Chinese Onset Group": record.get("mc_onset_group", ""),
                "Middle Chinese Rhyme Group": record.get("mc_rhyme_group", ""),
            }
        )
    return rows


def parse_search(search: str | None) -> dict[str, str]:
    if not search:
        return {}
    parsed = parse_qs(search.lstrip("?"), keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in parsed.items()}


def make_search(**params: str) -> str:
    return "?" + urlencode(params)


def render_overview(record_count: int) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Step 4 visualization", className="eyebrow"),
                    html.H2("OC to MC flow diagram", className="title"),
                    html.P(
                        "Click a Sankey flow to open the exact correspondence detail table.",
                        className="subtitle",
                    ),
                ],
                className="hero",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Show correspondences"),
                            dcc.Dropdown(
                                id="threshold-dropdown",
                                options=[
                                    {"label": "Show all", "value": "all"},
                                    {"label": "Hide 1 or fewer", "value": "1"},
                                    {"label": "Hide 3 or fewer", "value": "3"},
                                    {"label": "Hide 5 or fewer", "value": "5"},
                                ],
                                value="all",
                                clearable=False,
                            ),
                        ],
                        className="control-box",
                    ),
                    html.Div(
                        [
                            html.Label("Linkage view"),
                            dcc.Tabs(
                                id="linkage-tabs",
                                value="oc_onset|mc_onset_group",
                                children=[
                                    dcc.Tab(label="OC onset → MC onset group", value="oc_onset|mc_onset_group"),
                                    dcc.Tab(label="OC rhyme → MC rhyme group", value="oc_rhyme|mc_rhyme_group"),
                                ],
                            ),
                        ],
                        className="control-box",
                    ),
                ],
                className="controls-row",
            ),
            html.Div(
                [
                    html.Div(f"Records: {record_count:,}", className="stat-pill"),
                    html.Div("Flow click: enabled", className="stat-pill"),
                ],
                className="stats-row",
            ),
            dcc.Graph(id="sankey-graph", config={"displayModeBar": True}),
            html.Div(id="overview-meta", className="subtitle"),
            html.H4("Top correspondences"),
            dash_table.DataTable(
                id="overview-table",
                columns=[
                    {"name": "source", "id": "source"},
                    {"name": "target", "id": "target"},
                    {"name": "count", "id": "count"},
                ],
                page_size=20,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "6px"},
                style_header={"fontWeight": "bold"},
            ),
        ],
        className="page-wrap",
    )


def render_detail(
    source_field: str,
    target_field: str,
    source: str,
    target: str,
    rows: list[dict[str, object]],
) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Step 4 detail view", className="eyebrow"),
                    html.H2(f"{source_field} → {target_field}", className="title"),
                    html.P(
                        [
                            f"Correspondence: {source} → {target}. ",
                            html.A("Back to overview", href="?view=overview"),
                        ],
                        className="subtitle",
                    ),
                ],
                className="hero",
            ),
            html.Div(f"Matching rows: {len(rows):,}", className="stat-pill"),
            dash_table.DataTable(
                columns=[
                    {"name": "index", "id": "index"},
                    {"name": "character", "id": "character"},
                    {"name": "Old Chinese Reconstruction", "id": "Old Chinese Reconstruction"},
                    {"name": "Middle Chinese Onset Group", "id": "Middle Chinese Onset Group"},
                    {"name": "Middle Chinese Rhyme Group", "id": "Middle Chinese Rhyme Group"},
                ],
                data=rows,
                page_size=25,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "6px"},
                style_header={"fontWeight": "bold"},
            ),
        ],
        className="page-wrap",
    )


summary = load_summary(DEFAULT_LINKAGE_PATH)
records = load_records(DEFAULT_RECORDS_PATH)

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
    ]
)


@app.callback(Output("page-content", "children"), Input("url", "search"))
def render_page(search: str | None):
    params = parse_search(search)
    view = params.get("view", "overview")
    if view == "detail":
        source_field = params.get("source_field", "")
        target_field = params.get("target_field", "")
        source = params.get("source", "")
        target = params.get("target", "")
        rows = build_detail_rows(records, source_field, target_field, source, target)
        return render_detail(source_field, target_field, source, target, rows)
    return render_overview(int(summary["record_count"]))


@app.callback(
    Output("sankey-graph", "figure"),
    Output("overview-table", "data"),
    Output("overview-meta", "children"),
    Input("linkage-tabs", "value"),
    Input("threshold-dropdown", "value"),
)
def update_overview(tab_value: str, threshold_value: str):
    source_field, target_field = tab_value.split("|", 1)
    linkage = get_linkage(summary, source_field, target_field)
    visible_links = filter_links(linkage["links"], parse_threshold(threshold_value))

    fig = build_sankey(visible_links, source_field, target_field)
    table_data = visible_links[:200]
    meta = f"Visible links: {len(visible_links):,} · Visible weight: {sum(link['count'] for link in visible_links):,}"
    return fig, table_data, meta


@app.callback(
    Output("url", "search"),
    Input("sankey-graph", "clickData"),
    State("linkage-tabs", "value"),
    prevent_initial_call=True,
)
def open_detail_from_flow(click_data: dict | None, tab_value: str):
    if not click_data:
        return no_update

    points = click_data.get("points", [])
    if not points:
        return no_update

    point = points[0]
    customdata = point.get("customdata")
    if not customdata:
        return no_update

    text = str(customdata)
    if "|||" not in text:
        return no_update

    source, target = text.split("|||", 1)
    source_field, target_field = tab_value.split("|", 1)
    return make_search(
        view="detail",
        source_field=source_field,
        target_field=target_field,
        source=source,
        target=target,
    )


if __name__ == "__main__":
    app.run(debug=True)
