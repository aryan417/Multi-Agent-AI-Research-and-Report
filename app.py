import re
from io import BytesIO
from xml.sax.saxutils import escape

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from pipeline import run_search_pipeline

st.set_page_config(page_title="Research Assistant", page_icon="🔎", layout="wide")


# ---------- helpers ----------
def to_text(value) -> str:
    """Agent outputs can be str or a list of content blocks; normalise to str."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)
    return str(value)


def clean(text: str) -> str:
    """Replace characters the built-in PDF fonts can't render."""
    repl = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u2022": "-",
        "\u00a0": " ",
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "ignore").decode("latin-1")


def inline_md(text: str) -> str:
    """Convert **bold**, *italic*, `code` to ReportLab markup (after escaping)."""
    text = escape(clean(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
    return text


def markdown_to_pdf(title: str, markdown_text: str) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        title=title,
    )
    base = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=base["BodyText"], fontSize=10.5, leading=15, spaceAfter=6)
    h1 = ParagraphStyle("H1", parent=base["Heading1"], fontSize=18, spaceBefore=10, spaceAfter=8)
    h2 = ParagraphStyle("H2", parent=base["Heading2"], fontSize=14, spaceBefore=10, spaceAfter=6)
    h3 = ParagraphStyle("H3", parent=base["Heading3"], fontSize=12, spaceBefore=8, spaceAfter=4)

    story = [Paragraph(inline_md(title), base["Title"]), Spacer(1, 12)]
    bullets = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            story.append(
                ListFlowable(
                    [ListItem(Paragraph(inline_md(b), body)) for b in bullets],
                    bulletType="bullet", start="-", leftIndent=16,
                )
            )
            bullets = []

    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_bullets()
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        b = re.match(r"^\s*[-*+]\s+(.*)", line) or re.match(r"^\s*\d+[.)]\s+(.*)", line)
        if m:
            flush_bullets()
            level = len(m.group(1))
            style = h1 if level == 1 else h2 if level == 2 else h3
            story.append(Paragraph(inline_md(m.group(2)), style))
        elif b:
            bullets.append(b.group(1))
        else:
            flush_bullets()
            story.append(Paragraph(inline_md(line), body))
    flush_bullets()

    doc.build(story)
    return buf.getvalue()


# ---------- UI ----------
st.title("🔎 AI Research Assistant")
st.caption("Search → Scrape → Write → Critique")

with st.sidebar:
    st.header("About")
    st.write(
        "Enter a topic and the pipeline will search the web, scrape the best "
        "source, write a report, and have a critic review it."
    )
    if st.button("Clear results", use_container_width=True):
        st.session_state.pop("result", None)
        st.session_state.pop("topic", None)
        st.rerun()

topic = st.text_input("Research topic", placeholder="e.g. Latest advances in solid-state batteries")
run = st.button("Run research", type="primary", disabled=not topic.strip())

if run:
    try:
        with st.status("Running research pipeline...", expanded=True) as status:
            st.write("Searching, scraping, writing and reviewing. This can take a minute or two.")
            result = run_search_pipeline(topic.strip())
            status.update(label="Done!", state="complete", expanded=False)
        st.session_state["result"] = result
        st.session_state["topic"] = topic.strip()
    except Exception as e:
        st.error(f"Pipeline failed: {e}")

result = st.session_state.get("result")
if result:
    saved_topic = st.session_state.get("topic", "report")
    report = to_text(result.get("report", ""))
    feedback = to_text(result.get("feedback", ""))

    tab_report, tab_feedback, tab_search, tab_scrape = st.tabs(
        ["📄 Report", "🧐 Critic feedback", "🔍 Search results", "🌐 Scraped content"]
    )

    with tab_report:
        st.markdown(report)
        st.download_button(
            "⬇️ Download report as PDF",
            data=markdown_to_pdf(saved_topic.title(), report),
            file_name=re.sub(r"\W+", "_", saved_topic.lower()).strip("_") + "_report.pdf",
            mime="application/pdf",
            type="primary",
        )

    with tab_feedback:
        st.markdown(feedback)

    with tab_search:
        st.markdown(to_text(result.get("search_results", "")))

    with tab_scrape:
        st.markdown(to_text(result.get("scraped_content", "")))