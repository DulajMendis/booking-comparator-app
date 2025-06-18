
import streamlit as st
import fitz  # PyMuPDF
import difflib
import pandas as pd
from io import BytesIO
from difflib import SequenceMatcher

st.set_page_config(page_title="Booking List Comparator", layout="centered")
st.title("📘 Booking List Comparator")
st.write("Upload two PDF booking lists. This app compares all details and highlights changes.")

def extract_text(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    return text

def get_dossiers(text):
    import re
    entries = re.findall(r'DOSSIER.*?(?=\n\s*DOSSIER|\Z)', text, re.DOTALL)
    return entries

def parse_dossier(entry):
    import re
    fields = {}
    lines = entry.splitlines()
    fields["dossier"] = next((l.strip().split()[0] for l in lines if re.match(r'\d{7}', l.strip())), "")
    fields["names"] = [l.strip() for l in lines if re.search(r'\bMR\b|\bMM\b|\bCH\b', l)]
    fields["flights"] = [l.strip() for l in lines if re.search(r'\b[A-Z]{2}\s+\d{1,4}', l)]
    fields["tel"] = next((l.strip() for l in lines if "TELEPHONE" in l.upper()), "")
    return fields

def highlight_diff(a, b):
    sm = SequenceMatcher(None, a, b)
    result_a = ""
    result_b = ""
    for opcode, i1, i2, j1, j2 in sm.get_opcodes():
        if opcode == 'equal':
            result_a += a[i1:i2]
            result_b += b[j1:j2]
        elif opcode in ['replace', 'delete']:
            result_a += f"[{a[i1:i2]}]"
        if opcode in ['replace', 'insert']:
            result_b += f"[{b[j1:j2]}]"
    return result_a, result_b

file1 = st.file_uploader("Upload Previous Week's Booking List (PDF)", type="pdf")
file2 = st.file_uploader("Upload Current Week's Booking List (PDF)", type="pdf")

if file1 and file2:
    with st.spinner("Processing files and comparing..."):
        text1 = extract_text(file1)
        text2 = extract_text(file2)

        dossiers1 = get_dossiers(text1)
        dossiers2 = get_dossiers(text2)

        parsed1 = {d["dossier"]: d for d in map(parse_dossier, dossiers1) if d["dossier"]}
        parsed2 = {d["dossier"]: d for d in map(parse_dossier, dossiers2) if d["dossier"]}

        results = []
        for did in parsed1:
            if did not in parsed2:
                results.append((did, "DOSSIER", "REMOVED", "Only in old file", ""))
            else:
                f1, f2 = parsed1[did], parsed2[did]
                for k in ["names", "flights", "tel"]:
                    v1 = "\n".join(f1.get(k, [])) if isinstance(f1.get(k), list) else f1.get(k, "")
                    v2 = "\n".join(f2.get(k, [])) if isinstance(f2.get(k), list) else f2.get(k, "")
                    if v1 != v2:
                        old, new = highlight_diff(v1, v2)
                        results.append((did, k.upper(), "CHANGED", old, new))

        for did in parsed2:
            if did not in parsed1:
                results.append((did, "DOSSIER", "ADDED", "", "Only in new file"))

        df = pd.DataFrame(results, columns=["Dossier", "Field", "Status", "Old Value", "New Value"])

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Field-Level Changes')
            worksheet = writer.sheets['Field-Level Changes']
            for col in range(df.shape[1]):
                worksheet.set_column(col, col, 40)

        st.success("Comparison complete!")
        st.download_button("📥 Download Excel Report", data=output.getvalue(), file_name="Booking_Comparison.xlsx")
        st.dataframe(df)
else:
    st.info("Please upload both PDFs to proceed.")


st.markdown("<div style='margin-top: 50px; text-align: center; font-size: 0.9em; color: gray;'>Made with ♥️ by Dulaj for Connaissance De Ceylan</div>", unsafe_allow_html=True)
