from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from urllib.parse import urlencode

import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
DEFAULT_LINKAGE_PATH = ROOT / "data" / "oc_mc_linkages.json"


st.set_page_config(
    page_title="OC to MC flow",
    page_icon="flowchart",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_summary(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_records(path: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def get_linkage(summary: dict[str, object], source_field: str, target_field: str) -> dict[str, object]:
    for linkage in summary["linkages"]:
        if linkage["source_field"] == source_field and linkage["target_field"] == target_field:
            return linkage
    raise KeyError(f"{source_field} -> {target_field}")


def filter_links(links: list[dict[str, object]], *, hide_at_most: int) -> list[dict[str, object]]:
    filtered: list[dict[str, object]] = []
    for link in links:
        count = int(link["count"])
        if count <= hide_at_most:
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
    node_customdata = [f"source|{label}" for label in source_nodes] + [f"target|{label}" for label in target_nodes]

    link_sources = [indices[str(link["source"])] for link in links]
    link_targets = [indices[str(link["target"])] for link in links]
    link_values = [int(link["count"]) for link in links]

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
                    customdata=node_customdata,
                    hovertemplate="%{customdata}<extra></extra>",
                    color=node_colors,
                ),
                link=dict(source=link_sources, target=link_targets, value=link_values, color=link_color),
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


def summarize_counts(target: dict[str, object]) -> tuple[int, int]:
    links = target["links"]
    return len(links), sum(int(link["count"]) for link in links)


def build_detail_url(source_field: str, target_field: str, source: str, target: str) -> str:
    query = urlencode(
        {
            "view": "detail",
            "source_field": source_field,
            "target_field": target_field,
            "source": source,
            "target": target,
        }
    )
    return f"?{query}"


def build_correspondence_table(
    links: list[dict[str, object]],
    source_field: str,
    target_field: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for link in links:
        source = str(link["source"])
        target = str(link["target"])
        rows.append(
            {
                "source": source,
                "target": target,
                "count": int(link["count"]),
                "details_url": build_detail_url(source_field, target_field, source, target),
            }
        )
    return rows


def get_query_param(params: object, key: str, default: str = "") -> str:
    value = getattr(params, "get", lambda *_: default)(key, default)
    if isinstance(value, list):
        return value[0] if value else default
    return str(value)


def build_detail_rows(
    records: list[dict[str, object]],
    source_field: str,
    target_field: str,
    source: str,
    target: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    row_number = 0
    for record in records:
        if str(record.get(source_field, "")).strip() != source:
            continue
        if str(record.get(target_field, "")).strip() != target:
            continue
        row_number += 1
        rows.append(
            {
                "index": row_number,
                "character": record.get("character", ""),
                "Old Chinese Reconstruction": f"{record.get('oc_form_raw', '')} ({record.get('oc_form_clean', '')})",
                "Middle Chinese Onset Group": record.get("mc_onset_group", ""),
                "Middle Chinese Rhyme Group": record.get("mc_rhyme_group", ""),
            }
        )
    return rows


def get_selection_payload(event: object) -> list[dict[str, object]]:
    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection")
    if selection is None:
        return []
    points = getattr(selection, "points", None)
    if points is None and isinstance(selection, dict):
        points = selection.get("points")
    return list(points or [])


def get_point_customdata(point: object) -> str | None:
    customdata = point.get("customdata") if isinstance(point, dict) else getattr(point, "customdata", None)
    if customdata is None:
        return None
    if isinstance(customdata, list):
        return str(customdata[0]) if customdata else None
    return str(customdata)


def set_query_params(**params: str) -> None:
    st.query_params.clear()
    for key, value in params.items():
        st.query_params[key] = value


summary = load_summary(str(DEFAULT_LINKAGE_PATH))
records = load_records(str(ROOT / "data" / "baxter_sagart_records.oc_parsed.ndjson"))
query_params = st.query_params
view_mode = get_query_param(query_params, "view", "overview")

st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(31, 111, 120, 0.12), transparent 28%),
                    radial-gradient(circle at top right, rgba(201, 123, 44, 0.12), transparent 24%),
                    linear-gradient(180deg, #f6f1e7 0%, #fbfaf7 34%, #ffffff 100%);
            }
            .hero {
                padding: 1.4rem 1.5rem 1rem 1.5rem;
                border: 1px solid rgba(28, 39, 51, 0.08);
                border-radius: 22px;
                background: rgba(255, 255, 255, 0.78);
                box-shadow: 0 16px 48px rgba(23, 30, 39, 0.08);
            }
            .eyebrow {
                text-transform: uppercase;
                letter-spacing: 0.18em;
                font-size: 0.72rem;
                color: #5a646f;
                margin-bottom: 0.4rem;
            }
            .title {
                font-size: 2.2rem;
                line-height: 1.05;
                font-weight: 700;
                color: #17202b;
                margin: 0 0 0.5rem 0;
            }
            .subtitle {
                font-size: 1rem;
                color: #4b5663;
                max-width: 78ch;
            }
            .card {
                padding: 1rem 1rem 0.9rem 1rem;
                border-radius: 16px;
                border: 1px solid rgba(28, 39, 51, 0.08);
                background: rgba(255, 255, 255, 0.84);
                box-shadow: 0 10px 30px rgba(23, 30, 39, 0.05);
            }
            .metric-label {
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #66707b;
                margin-bottom: 0.25rem;
            }
            .metric-value {
                font-size: 1.6rem;
                font-weight: 700;
                color: #17202b;
            }
            .metric-note {
                font-size: 0.82rem;
                color: #5e6974;
                margin-top: 0.15rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
)

if view_mode == "node_detail":
    source_field = get_query_param(query_params, "source_field")
    target_field = get_query_param(query_params, "target_field")
    node_role = get_query_param(query_params, "node_role")
    node_label = get_query_param(query_params, "node_label")

    def node_matches(record: dict[str, object]) -> bool:
        if node_role == "source":
            return str(record.get(source_field, "")).strip() == node_label
        return str(record.get(target_field, "")).strip() == node_label

    node_rows = []
    for row_number, record in enumerate(records, start=1):
        if not node_matches(record):
            continue
        node_rows.append(
            {
                "index": len(node_rows) + 1,
                "character": record.get("character", ""),
                "Old Chinese Reconstruction": f"{record.get('oc_form_raw', '')} ({record.get('oc_form_clean', '')})",
                "Middle Chinese Onset Group": record.get("mc_onset_group", ""),
                "Middle Chinese Rhyme Group": record.get("mc_rhyme_group", ""),
            }
        )

    st.markdown(
        f"""
        <div class="hero">
          <div class="eyebrow">Step 4 detail view</div>
          <div class="title">{source_field} → {target_field}</div>
          <div class="subtitle">Node: {node_role} = {node_label}. <a href="?view=overview">Back to overview</a>.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    metric_cols = st.columns(3)
    metric_cols[0].markdown(
        f'<div class="card"><div class="metric-label">Node</div><div class="metric-value">{node_label}</div><div class="metric-note">{node_role} node</div></div>',
        unsafe_allow_html=True,
    )
    metric_cols[1].markdown(
        f'<div class="card"><div class="metric-label">Matching rows</div><div class="metric-value">{len(node_rows):,}</div><div class="metric-note">characters attached to this node</div></div>',
        unsafe_allow_html=True,
    )
    metric_cols[2].markdown(
        f'<div class="card"><div class="metric-label">Records</div><div class="metric-value">{summary["record_count"]:,}</div><div class="metric-note">parsed NDJSON entries</div></div>',
        unsafe_allow_html=True,
    )

    st.write("")
    if node_rows:
        st.dataframe(node_rows, width="stretch", hide_index=True)
    else:
        st.warning("No rows found for this node.")
    st.stop()

if view_mode == "detail":
        source_field = get_query_param(query_params, "source_field")
        target_field = get_query_param(query_params, "target_field")
        source = get_query_param(query_params, "source")
        target = get_query_param(query_params, "target")
        detail_rows = build_detail_rows(records, source_field, target_field, source, target)

        st.markdown(
                f"""
                <div class="hero">
                    <div class="eyebrow">Step 4 detail view</div>
                    <div class="title">{source_field} → {target_field}</div>
                    <div class="subtitle">All records sharing this correspondence. Click <a href="?view=overview">back to overview</a> to return to the Sankey view.</div>
                </div>
                """,
                unsafe_allow_html=True,
        )

        st.write("")
        metric_cols = st.columns(3)
        metric_cols[0].markdown(
                f'<div class="card"><div class="metric-label">Correspondence</div><div class="metric-value">{source} → {target}</div><div class="metric-note">selected link</div></div>',
                unsafe_allow_html=True,
        )
        metric_cols[1].markdown(
                f'<div class="card"><div class="metric-label">Characters</div><div class="metric-value">{len(detail_rows):,}</div><div class="metric-note">rows sharing this correspondence</div></div>',
                unsafe_allow_html=True,
        )
        metric_cols[2].markdown(
                f'<div class="card"><div class="metric-label">Records</div><div class="metric-value">{summary["record_count"]:,}</div><div class="metric-note">parsed NDJSON entries</div></div>',
                unsafe_allow_html=True,
        )

        st.write("")
        if detail_rows:
                st.dataframe(detail_rows, width="stretch", hide_index=True)
        else:
                st.warning("No rows found for this correspondence.")
        st.stop()

threshold_choice = st.sidebar.radio(
        "Show correspondences",
        options=["Show all", "Hide 1 or fewer", "Hide 3 or fewer", "Hide 5 or fewer"],
        index=0,
)
hide_at_most = None if threshold_choice == "Show all" else int(threshold_choice.split()[1])

st.sidebar.markdown("---")
st.sidebar.caption("The Sankey and correspondence table both use the same visibility setting.")

linkage_specs = [
        get_linkage(summary, "oc_onset", "mc_onset_group"),
        get_linkage(summary, "oc_rhyme", "mc_rhyme_group"),
]

st.markdown(
        f"""
        <div class="hero">
            <div class="eyebrow">Step 4 visualization</div>
            <div class="title">OC to MC flow diagram</div>
            <div class="subtitle">
                This dashboard shows two interactive Sankey views: OC onset → MC onset group, and OC rhyme → MC rhyme group.
                You can also open a detail page for any correspondence to see every matching character.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
)

st.write("")

metric_cols = st.columns(4)
metric_cols[0].markdown(
        f'<div class="card"><div class="metric-label">Records</div><div class="metric-value">{summary["record_count"]:,}</div><div class="metric-note">parsed entries in the NDJSON</div></div>',
        unsafe_allow_html=True,
)
metric_cols[1].markdown(
        f'<div class="card"><div class="metric-label">Linkage views</div><div class="metric-value">{len(linkage_specs):,}</div><div class="metric-note">onset and rhyme flows</div></div>',
        unsafe_allow_html=True,
)
metric_cols[2].markdown(
        f'<div class="card"><div class="metric-label">Correspondence filter</div><div class="metric-value">{threshold_choice}</div><div class="metric-note">applies to both Sankey and table</div></div>',
        unsafe_allow_html=True,
)
metric_cols[3].markdown(
        f'<div class="card"><div class="metric-label">Summary blocks</div><div class="metric-value">{len(summary["linkages"]):,}</div><div class="metric-note">linkage blocks in the JSON</div></div>',
        unsafe_allow_html=True,
)

st.write("")
tabs = st.tabs(["OC onset → MC onset group", "OC rhyme → MC rhyme group"])

for tab, linkage in zip(tabs, linkage_specs):
        with tab:
                if hide_at_most is None:
                        visible_links = [
                                {"source": str(link["source"]), "target": str(link["target"]), "count": int(link["count"])}
                                for link in linkage["links"]
                        ]
                else:
                        visible_links = filter_links(linkage["links"], hide_at_most=hide_at_most)

                visible_count = sum(link["count"] for link in visible_links)
                all_link_count, all_weight = summarize_counts(linkage)
                table_rows = build_correspondence_table(visible_links, linkage["source_field"], linkage["target_field"])

                left, right = st.columns([1.6, 1])

                with left:
                    st.subheader(f"{linkage['source_field']} → {linkage['target_field']}")
                    if visible_links:
                        sankey_event = st.plotly_chart(
                            build_sankey(visible_links, linkage["source_field"], linkage["target_field"]),
                            width="stretch",
                            key=f"{linkage['source_field']}-{linkage['target_field']}",
                            on_select="rerun",
                            selection_mode="points",
                        )
                        selected_points = get_selection_payload(sankey_event)
                        if selected_points:
                            selected_customdata = get_point_customdata(selected_points[0])
                            if selected_customdata and "|" in selected_customdata:
                                node_role, node_label = selected_customdata.split("|", 1)
                                set_query_params(
                                    view="node_detail",
                                    source_field=linkage["source_field"],
                                    target_field=linkage["target_field"],
                                    node_role=node_role,
                                    node_label=node_label,
                                )
                                st.rerun()
                    else:
                        st.info("No links match the selected visibility setting.")

                with right:
                    st.subheader("Correspondence table")
                    st.caption("Click Details to open the full character list for a correspondence.")
                    st.dataframe(
                        table_rows,
                            width="stretch",
                        hide_index=True,
                        column_config={"details_url": st.column_config.LinkColumn("Details", display_text="Open")},
                        )

                st.write("")
                source_col, summary_col = st.columns([1, 1])

                with source_col:
                        st.subheader("Top OC nodes")
                        st.caption("Raw source-frequency view from the linkage summary.")
                        st.dataframe(linkage["source_totals"][:25], width="stretch", hide_index=True)

                with summary_col:
                        st.markdown(
                                f"""
                                <div class="card">
                                    <div class="metric-label">Visible links</div>
                                    <div class="metric-value">{len(visible_links):,}</div>
                                    <div class="metric-note">visible after the chosen filter</div>
                                    <div style="height:0.7rem"></div>
                                    <div class="metric-label">Visible weight</div>
                                    <div class="metric-value">{visible_count:,}</div>
                                    <div class="metric-note">sum of visible link counts</div>
                                    <div style="height:0.7rem"></div>
                                    <div class="metric-label">All links</div>
                                    <div class="metric-value">{all_link_count:,}</div>
                                    <div class="metric-note">total links, weight {all_weight:,}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                        )
