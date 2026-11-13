"""
ReportSathi - AI Lab Report & Prescription Explainer
Built with Streamlit, PyMuPDF, and the Google GenAI SDK.
Explains medical reports in plain everyday language (English & Kannada) with strict safety boundaries.
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from extractor import extract_from_pdf, prepare_image, validate_upload, ExtractionError
from analyzer import analyze_report, AnalyzerError

# Set Streamlit page configuration
st.set_page_config(
    page_title="ReportSathi - Lab Report Explainer",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean, readable medical cards and flag badges
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .privacy-notice {
        font-size: 0.85rem;
        background-color: #F3F4F6;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 4px solid #9CA3AF;
        margin-bottom: 1.5rem;
        color: #374151;
    }
    .disclaimer-box {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 12px 16px;
        border-radius: 6px;
        color: #92400E;
        font-size: 0.95rem;
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
    }
    .urgent-banner {
        background-color: #FEE2E2;
        border: 2px solid #EF4444;
        border-radius: 8px;
        padding: 16px;
        color: #991B1B;
        margin-bottom: 1.5rem;
    }
    .urgent-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .test-card {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-normal {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-high {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-low {
        background-color: #FEF08A;
        color: #713F12;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-unknown {
        background-color: #F3F4F6;
        color: #4B5563;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
</style>
""", unsafe_allow_html=True)


def get_flag_badge_html(flag: str) -> str:
    flag_lower = (flag or "unknown").lower()
    if flag_lower == "normal":
        return '<span class="badge-normal">🟢 Normal</span>'
    elif flag_lower == "high":
        return '<span class="badge-high">🔴 High</span>'
    elif flag_lower == "low":
        return '<span class="badge-low">🟡 Low</span>'
    else:
        return '<span class="badge-unknown">⚪ Unclear / Unspecified</span>'


def main():
    # Header
    st.markdown('<div class="main-title">🩺 ReportSathi (ವರದಿ ಸಾಥಿ)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Understand medical lab reports in simple, everyday language — in English or ಕನ್ನಡ (Kannada).</div>',
        unsafe_allow_html=True
    )

    # Privacy line
    st.markdown(
        '<div class="privacy-notice">🔒 <strong>Privacy First:</strong> Files are processed strictly in-memory. '
        'Your medical reports are never saved to disk, logged, or retained anywhere.</div>',
        unsafe_allow_html=True
    )

    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Settings & Configuration")

        # Language selection
        language_choice = st.radio(
            "Select Language / ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ",
            options=["English", "Kannada (ಕನ್ನಡ)"],
            index=0,
            help="Choose the language for plain-language explanations."
        )

        st.markdown("---")

        # API Key Resolution
        env_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        env_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

        st.subheader("Google Gemini Settings")
        user_api_key = st.text_input(
            "Gemini API Key",
            value=env_api_key,
            type="password",
            placeholder="Paste AI Studio Key here or set in .env",
            help="Free key from https://aistudio.google.com/app/apikey"
        )
        api_key = user_api_key.strip() if user_api_key.strip() else env_api_key

        model_name = st.text_input(
            "Gemini Model",
            value=env_model,
            help="Configurable Gemini model name (e.g., gemini-2.5-flash, gemini-2.0-flash)."
        )

        st.markdown("---")
        st.markdown(
            "**Need an API Key?**\n"
            "1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)\n"
            "2. Generate a free API key\n"
            "3. Paste it above or add `GEMINI_API_KEY=...` to your `.env` file."
        )

    # Check for API Key presence
    if not api_key:
        st.warning(
            "⚠️ **Gemini API Key Required:** Please provide your Gemini API key in the sidebar or "
            "add `GEMINI_API_KEY=your_key` in a `.env` file in the project folder to enable analysis."
        )

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload your Lab Report (PDF, JPG, or PNG — Max 10 MB)",
        type=["pdf", "jpg", "jpeg", "png"],
        help="Upload digital PDFs, scanned documents, or phone photos of lab results."
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_name = uploaded_file.name

        # Process button
        analyze_btn = st.button("🔍 Explain My Report", type="primary", use_container_width=True)

        if analyze_btn:
            if not api_key:
                st.error("Cannot proceed without an API Key. Please enter your Gemini API Key in the left sidebar.")
                return

            try:
                # 1. Validation
                with st.spinner("Validating uploaded file..."):
                    ext = validate_upload(file_bytes, file_name)

                # 2. In-memory extraction
                with st.spinner("Reading report content..."):
                    if ext == ".pdf":
                        extracted_data = extract_from_pdf(pdf_bytes=file_bytes, max_pages=5)
                        if extracted_data.get("mode") == "scanned_pdf":
                            st.info(
                                f"ℹ️ The PDF has minimal selectable text. Running visual OCR on {extracted_data['pages_processed']} rendered page(s)..."
                            )
                    else:
                        extracted_data = prepare_image(image_bytes=file_bytes, ext=ext)

                # 3. AI Analysis with Google GenAI
                with st.spinner(f"Analyzing report and preparing explanations in {language_choice}..."):
                    report = analyze_report(
                        extracted_data=extracted_data,
                        language=language_choice,
                        api_key=api_key,
                        model_name=model_name
                    )

                st.session_state["report_analysis"] = report
                st.session_state["report_lang"] = language_choice

            except ExtractionError as ee:
                st.error(f"❌ Document Error: {str(ee)}")
                return
            except AnalyzerError as ae:
                st.error(f"❌ Analysis Error: {str(ae)}")
                return
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {str(e)}")
                return

    # Display Analysis Results
    if "report_analysis" in st.session_state:
        report = st.session_state["report_analysis"]
        lang = st.session_state.get("report_lang", "English")

        st.markdown("---")

        # Check if fallback occurred
        if report.get("parse_fallback"):
            st.warning("⚠️ **Note on Output:** We could not automatically format the response into standard tables.")
            st.info("Here is the raw explanation provided by the assistant:")
            st.write(report.get("raw_text", ""))
            return

        # Check if document is a lab report
        if not report.get("is_lab_report", True):
            st.warning(
                "📄 **Not Recognized as a Lab Report:**\n\n"
                f"{report.get('summary', 'The uploaded file does not appear to be a recognized medical diagnostic test report or prescription. Please verify and upload a lab test report.')}"
            )
            return

        # Urgent Attention Banner (if flagged)
        if report.get("urgent_attention"):
            urgent_reason = report.get("urgent_reason") or "Certain test values fall significantly outside critical reference ranges."
            st.markdown(
                f"""
                <div class="urgent-banner">
                    <div class="urgent-title">🚨 Urgent Medical Notice</div>
                    <div><strong>This result may need prompt medical attention. Contact your doctor now. If you feel very unwell, call emergency services (112 in India) or go to the nearest hospital.</strong></div>
                    <div style="margin-top: 8px; font-size: 0.95rem;"><em>Reason flagged:</em> {urgent_reason}</div>
                    <div style="margin-top: 6px; font-size: 0.85rem; color: #7F1D1D;">Do not delay professional medical consultation or rely on this tool during an emergency.</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Standard Mandatory Medical Disclaimer
        st.markdown(
            """
            <div class="disclaimer-box">
                ⚖️ <strong>Important Disclaimer:</strong> ReportSathi explains what tests measure in simple words. 
                It is not a doctor and cannot diagnose or advise treatment. Always confirm with your doctor.
            </div>
            """,
            unsafe_allow_html=True
        )

        # Summary Section
        st.subheader("📋 Overall Summary")
        summary_text = report.get("summary", "No summary available.")
        st.write(summary_text)

        report_date = report.get("report_date")
        if report_date:
            st.caption(f"📅 Report Date detected: {report_date}")

        st.markdown("---")

        # Table Section (a): Check against paper report
        st.subheader("📊 Extracted Test Values")
        st.caption("🔍 **Please check these against your paper report** (Optical character recognition can misread small digits or decimal points).")

        results = report.get("results", [])
        if results:
            table_rows = []
            for r in results:
                table_rows.append({
                    "Test Name": r.get("test", "—"),
                    "Observed Value": r.get("value", "—"),
                    "Unit": r.get("unit", "—"),
                    "Printed Reference Range": r.get("reference_range") if r.get("reference_range") else "None printed",
                    "Status": (r.get("flag") or "unknown").upper()
                })
            st.dataframe(table_rows, use_container_width=True)
        else:
            st.info("No specific numeric test parameters were identified in this document.")

        st.markdown("---")

        # Detailed Plain-Language Explanation Cards Section (b)
        st.subheader("💡 Plain-Language Explanations")
        st.caption("Here is what each test measures in simple words:")

        if results:
            for item in results:
                test_name = item.get("test", "Test Parameter")
                value = item.get("value", "")
                unit = item.get("unit", "")
                ref_range = item.get("reference_range") or "Not specified on report"
                flag = item.get("flag", "unknown")
                badge_html = get_flag_badge_html(flag)
                explanation = item.get("explanation", "No explanation available.")
                meaning = item.get("what_it_may_mean", "")

                card_html = f"""
                <div class="test-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 1.15rem; font-weight: 700; color: #1F2937;">{test_name}</span>
                        {badge_html}
                    </div>
                    <div style="font-size: 0.9rem; color: #4B5563; margin-bottom: 8px;">
                        <strong>Reported Value:</strong> {value} {unit} &nbsp;|&nbsp; <strong>Printed Range:</strong> {ref_range}
                    </div>
                    <div style="margin-bottom: 6px; font-size: 0.95rem;">
                        <strong>What this measures:</strong> {explanation}
                    </div>
                    <div style="font-size: 0.92rem; color: #374151; background: #F9FAFB; padding: 8px 12px; border-radius: 6px;">
                        <strong>What it may mean (General context):</strong> {meaning}
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.write("No test breakdown available.")

        st.markdown("---")

        # Questions for Doctor Section (d)
        st.subheader("🩺 Questions You Can Ask Your Doctor")
        questions = report.get("questions_for_doctor", [])
        if questions:
            for q in questions:
                st.markdown(f"- ❓ **{q}**")
        else:
            st.markdown("- What do these results mean in the context of my current health and symptoms?")
            st.markdown("- Do any of these values require follow-up tests or changes in lifestyle?")


if __name__ == "__main__":
    main()
