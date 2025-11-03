import streamlit as st
import re
import pandas as pd
from PyPDF2 import PdfReader
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Question Paper Generator", page_icon="📄", layout="wide")
st.title("📄 Smart Question Paper Generator (Final Version)")

st.write("""
Upload your Question Bank PDF below to extract questions, edit them, assign marks, and generate a custom paper.
""")

# -------- PDF Text Extraction ----------
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


# -------- Unit + Question Detection ----------
def parse_text(text):
    unit_pattern = r"(?i)(?:UNIT|SECTION|PART)\s*(?:-|–|—|:)?\s*(\d+|[A-Z]|[IVXLC]+)"
    unit_matches = list(re.finditer(unit_pattern, text))
    if not unit_matches:
        return []

    units_data = []
    for i, match in enumerate(unit_matches):
        unit_name = match.group(0).strip()
        start = match.end()
        end = unit_matches[i + 1].start() if i + 1 < len(unit_matches) else len(text)
        content = text[start:end].strip()

        # Detect question numbering pattern
        question_patterns = [
            r"\d+\.", r"\d+\)", r"[a-z]\)", r"[A-Z]\)", r"\([a-z]\)"
        ]
        pattern_counts = {p: len(re.findall(p, content)) for p in question_patterns}
        question_pattern = max(pattern_counts, key=pattern_counts.get)

        parts = re.split(question_pattern, content)
        tokens = re.findall(question_pattern, content)
        questions = [f"{t} {p.strip()}" for t, p in zip(tokens, parts[1:]) if p.strip()]

        units_data.append({
            "Unit": unit_name,
            "Questions": questions
        })
    return units_data


# -------- PDF Generation ----------
def generate_pdf(selected_units):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x_margin, y = 50, height - 50

    total_marks = sum(
        int(q["Marks"]) for unit in selected_units for q in unit["Questions"] if q["Marks"].isdigit()
    )

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, y, "Question Paper")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 50, y, f"Total Marks: {total_marks}")
    y -= 40

    for unit_idx, unit in enumerate(selected_units, start=1):
        unit_marks = sum(int(q["Marks"]) for q in unit["Questions"] if q["Marks"].isdigit())

        if y < 100:
            c.showPage()
            y = height - 80

        c.setFont("Helvetica-Bold", 13)
        c.drawString(x_margin, y, "Answer the following:")
        c.drawRightString(width - 50, y, f"{unit_marks} Marks")
        y -= 25

        c.setFont("Helvetica", 11)
        q_no = 1
        for q in unit["Questions"]:
            marks_display = f" ({q['Marks']} Marks)" if q["Marks"] else ""
            text = f"Q{q_no}. {q['Question']}{marks_display}"

            if y < 80:
                c.showPage()
                y = height - 80
                c.setFont("Helvetica-Bold", 13)
                c.drawString(x_margin, y, "Answer the following:")
                c.drawRightString(width - 50, y, f"{unit_marks} Marks")
                y -= 25
                c.setFont("Helvetica", 11)

            c.drawString(x_margin, y, text)
            y -= 18
            q_no += 1
        y -= 20

    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


# -------- Streamlit App Logic ----------
uploaded_file = st.file_uploader("Upload Question Bank (PDF)", type=["pdf"])

if uploaded_file is not None:
    text = extract_text_from_pdf(uploaded_file)

    if not text.strip():
        st.error("⚠️ No text extracted. Ensure PDF is text-based (not scanned).")
    else:
        units_data = parse_text(text)
        if not units_data:
            st.warning("No valid units detected. Check your PDF formatting.")
        else:
            st.success(f"✅ {len(units_data)} Units/Sections Detected Successfully!")

            st.write("### ✏️ Select Questions, Edit Them, and Assign Marks")

            selected_units = []
            for unit_index, unit in enumerate(units_data):
                st.markdown(f"#### 🧩 {unit['Unit']}")
                selected_questions = []

                for q_index, q in enumerate(unit["Questions"]):
                    cols = st.columns([0.05, 0.7, 0.1, 0.15])

                    with cols[0]:
                        select = st.checkbox("", key=f"chk_{unit_index}_{q_index}")

                    with cols[1]:
                        # --- Edit question section ---
                        edit_key = f"edit_{unit_index}_{q_index}"
                        edited_question_key = f"edited_text_{unit_index}_{q_index}"

                        if st.session_state.get(edit_key, False):
                            new_text = st.text_area("Edit question", value=q, key=edited_question_key, height=100)
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("💾 Save", key=f"save_{unit_index}_{q_index}"):
                                    st.session_state[f"edited_value_{unit_index}_{q_index}"] = new_text
                                    st.session_state[edit_key] = False
                            with c2:
                                if st.button("❌ Cancel", key=f"cancel_{unit_index}_{q_index}"):
                                    st.session_state[edit_key] = False
                            q_display = st.session_state.get(f"edited_value_{unit_index}_{q_index}", q)
                        else:
                            q_display = st.session_state.get(f"edited_value_{unit_index}_{q_index}", q)
                            st.markdown(q_display)
                            if st.button("✏️ Edit", key=f"btn_{unit_index}_{q_index}"):
                                st.session_state[edit_key] = True

                    with cols[2]:
                        marks = st.text_input("Marks", value="", key=f"marks_{unit_index}_{q_index}")

                    if select:
                        selected_questions.append({
                            "Question": q_display,
                            "Marks": marks
                        })

                if selected_questions:
                    selected_units.append({
                        "Unit": unit["Unit"],
                        "Questions": selected_questions
                    })

            # --- Generate Question Paper ---
            if st.button("📄 Generate Question Paper (Preview & PDF)"):
                if not selected_units:
                    st.warning("Select at least one question to generate the paper.")
                else:
                    total_marks = sum(
                        int(q["Marks"]) for unit in selected_units for q in unit["Questions"] if q["Marks"].isdigit()
                    )

                    st.success("✅ Question Paper Preview Generated")
                    st.markdown(f"### **Question Paper**")
                    st.markdown(f"<div style='text-align: right; font-weight: bold;'>Total Marks: {total_marks}</div>", unsafe_allow_html=True)
                    st.markdown("---")

                    for unit_idx, unit in enumerate(selected_units, start=1):
                        unit_marks = sum(int(q["Marks"]) for q in unit["Questions"] if q["Marks"].isdigit())

                        st.markdown(
                            f"<div style='display:flex; justify-content:space-between; font-weight:bold;'>"
                            f"<span>Answer the following:</span>"
                            f"<span>{unit_marks} Marks</span></div>",
                            unsafe_allow_html=True,
                        )

                        q_no = 1
                        for q in unit["Questions"]:
                            marks_display = f"({q['Marks']} Marks)" if q["Marks"] else ""
                            st.markdown(f"**Q{q_no}. {q['Question']}** {marks_display}")
                            q_no += 1
                        st.markdown("---")

                    pdf_data = generate_pdf(selected_units)
                    st.download_button(
                        "📥 Download Question Paper (PDF)",
                        data=pdf_data,
                        file_name="Question_Paper.pdf",
                        mime="application/pdf",
                    )
else:
    st.info("👆 Upload your Question Bank PDF to begin.")
