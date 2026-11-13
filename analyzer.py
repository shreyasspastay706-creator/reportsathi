"""
ReportSathi - AI Lab Report Analyzer
Uses google-genai SDK to analyze extracted report text or images.
Implements strict medical safety rules, vernacular translation (English/Kannada),
robust JSON validation, and automatic single retry on malformed JSON.
"""

from typing import Dict, Any, List, Tuple
import json
import re
from google import genai
from google.genai import types
from google.genai.errors import APIError


SYSTEM_INSTRUCTION = """You are ReportSathi, an empathetic and cautious medical lab report interpreter.
Your goal is to help patients understand what their lab tests measure in everyday plain language.

STRICT MEDICAL SAFETY & ACCURACY RULES:
1. NEVER DIAGNOSE ANY DISEASE OR CONDITION.
2. NEVER RECOMMEND, START, STOP, OR CHANGE ANY MEDICINE, TREATMENT, OR DOSAGE.
3. NEVER SUGGEST HOME REMEDIES OR SELF-TREATMENT FOR AN ABNORMAL RESULT.
4. REFERENCE RANGES: Use ONLY the explicit reference ranges printed on this specific report. If no reference range is printed for a test, set "reference_range" to null and "flag" to "unknown". NEVER GUESS OR INVENT REFERENCE RANGES.
5. READABILITY: If any test name, value, unit, or range is blurred, smudged, cropped, or not clearly readable, DO NOT GUESS IT. Set flag to "unknown" and state clearly in the explanation that the value was unreadable on the document.
6. NOT A LAB REPORT: If the uploaded document is not a medical lab report or prescription, set "is_lab_report": false, "readable": false, and summarize politely in "summary" that the document does not appear to be a medical report.
7. URGENT ATTENTION: Set "urgent_attention": true ONLY IF there are critical, potentially life-threatening panic values (e.g., severe critical hypoglycemia, extreme potassium abnormalities, troponin spikes, critical hemoglobin < 6 g/dL, severe thrombocytopenia). Explain the urgency neutrally in "urgent_reason".
8. HEDGING: In "what_it_may_mean", always hedge carefully. Never say "You have X". Use cautious, non-diagnostic phrasing such as "A higher value can sometimes be seen in...", "This can be influenced by diet, hydration, or...", "Doctors sometimes evaluate this alongside other factors".
9. LANGUAGE REQUIREMENT:
   - If language is 'English', provide simple, clear, jargon-free explanations.
   - If language is 'Kannada' (ಕನ್ನಡ), provide warm, natural conversational Kannada (everyday spoken Kannada).
   - In Kannada, keep the medical test names in English inside parentheses right after the Kannada name (for example: ಹಿಮೋಗ್ಲೋಬಿನ್ (Hemoglobin)), because this is how people and doctors communicate in real life.

RESPONSE FORMAT:
You MUST respond with pure JSON only matching this exact schema:
{
  "is_lab_report": boolean,
  "readable": boolean,
  "report_date": string or null,
  "results": [
    {
      "test": string,
      "value": string,
      "unit": string,
      "reference_range": string or null,
      "flag": "normal" | "low" | "high" | "unknown",
      "explanation": string,
      "what_it_may_mean": string
    }
  ],
  "urgent_attention": boolean,
  "urgent_reason": string or null,
  "questions_for_doctor": [string, string, string],
  "summary": string
}
"""


class AnalyzerError(Exception):
    """Custom exception for user-friendly AI analysis errors."""
    pass


def clean_and_parse_json(raw_text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Safely parses JSON from model response text.
    Handles markdown code fences if present.
    Returns (parsed_dict, error_message).
    """
    if not raw_text or not raw_text.strip():
        return None, "Empty response received from analysis model."

    text = raw_text.strip()
    # Strip markdown code blocks if the model wrapped it
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return None, "Response JSON is not an object."

        # Validate essential top-level keys
        required_keys = ["is_lab_report", "readable", "results", "urgent_attention", "summary"]
        for key in required_keys:
            if key not in data:
                return None, f"Missing required field in response: '{key}'."

        # Ensure results is a list
        if not isinstance(data.get("results"), list):
            data["results"] = []

        # Normalize flags in results
        valid_flags = {"normal", "low", "high", "unknown"}
        for item in data.get("results", []):
            if isinstance(item, dict):
                flag = str(item.get("flag", "unknown")).lower()
                item["flag"] = flag if flag in valid_flags else "unknown"

        # Ensure questions_for_doctor is a list
        if not isinstance(data.get("questions_for_doctor"), list):
            data["questions_for_doctor"] = []

        return data, None
    except Exception as e:
        return None, f"JSON parsing error: {str(e)}"


def build_analysis_prompt(extracted_data: Dict[str, Any], language: str) -> Tuple[List[Any], str]:
    """
    Constructs the prompt contents and instructions based on language and extraction mode.
    """
    lang_instruction = "English (simple, everyday plain language)"
    if language.lower() in ("kannada", "kn", "ಕನ್ನಡ"):
        lang_instruction = (
            "Kannada (ಕನ್ನಡ). Translate all explanations and summaries into natural, everyday Kannada. "
            "Retain medical test names in English in parentheses, e.g., ಹಿಮೋಗ್ಲೋಬಿನ್ (Hemoglobin)."
        )

    mode = extracted_data.get("mode")
    prompt_text = (
        f"Target Language: {lang_instruction}\n"
        "Please analyze the following medical lab report. Carefully extract each test, its value, "
        "unit, and printed reference range. Evaluate the flags strictly based on the printed reference range. "
        "Follow all safety instructions and output only the required JSON format."
    )

    contents: List[Any] = []

    if mode == "text_pdf":
        text_content = extracted_data.get("text", "")
        contents.append(f"{prompt_text}\n\n--- REPORT TEXT START ---\n{text_content}\n--- REPORT TEXT END ---")
    elif mode == "scanned_pdf":
        contents.append(f"{prompt_text}\n\nThis is a scanned PDF report rendered page by page:")
        for idx, img_bytes in enumerate(extracted_data.get("images", [])):
            contents.append(f"Page {idx + 1}:")
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
    elif mode == "image":
        mime_type = extracted_data.get("mime_type", "image/jpeg")
        contents.append(f"{prompt_text}\n\nAttached is the image of the medical report:")
        for img_bytes in extracted_data.get("images", []):
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
    else:
        contents.append(prompt_text)

    return contents, lang_instruction


def analyze_report(
    extracted_data: Dict[str, Any],
    language: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Calls Google Gemini using the google-genai SDK.
    Includes retry logic on JSON failure and friendly error translation.
    """
    if not api_key or not api_key.strip():
        raise AnalyzerError(
            "Gemini API Key is not set. Please add GEMINI_API_KEY in your .env file."
        )

    client = genai.Client(api_key=api_key.strip())
    contents, _ = build_analysis_prompt(extracted_data, language)

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.1,  # Low temperature for factual extraction
    )

    def call_gemini(call_contents):
        try:
            return client.models.generate_content(
                model=model_name,
                contents=call_contents,
                config=config,
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "not found" in err_msg or "404" in err_msg or "invalid model" in err_msg:
                raise AnalyzerError(
                    f"The configured model '{model_name}' was not found or is unavailable. "
                    "Please update GEMINI_MODEL in your .env file to a supported model (e.g., gemini-2.5-flash or gemini-2.0-flash)."
                ) from e
            elif "quota" in err_msg or "rate limit" in err_msg or "429" in err_msg or "resource_exhausted" in err_msg:
                raise AnalyzerError(
                    "Google Gemini API quota or rate limit exceeded. Please wait a moment or check your Google AI Studio plan."
                ) from e
            elif "api_key" in err_msg or "unauthorized" in err_msg or "401" in err_msg or "403" in err_msg or "permission" in err_msg:
                raise AnalyzerError(
                    "Invalid or unauthorized Gemini API key. Please verify your GEMINI_API_KEY in the .env file."
                ) from e
            elif "connection" in err_msg or "network" in err_msg or "timeout" in err_msg:
                raise AnalyzerError(
                    "Network error while connecting to Gemini API. Please check your internet connection."
                ) from e
            else:
                raise AnalyzerError(f"Gemini API error: {str(e)}") from e

    # First Attempt
    response = call_gemini(contents)
    raw_text = response.text or ""
    parsed, parse_err = clean_and_parse_json(raw_text)

    if parsed is not None:
        return parsed

    # Retry Once if JSON parsing failed
    retry_prompt = [
        "Your previous output could not be parsed as valid JSON. "
        "Please regenerate your complete response strictly in valid JSON format matching the schema without any markdown formatting or unescaped characters.",
        f"Previous output snippet: {raw_text[:300]}"
    ]
    try:
        retry_response = call_gemini(contents + retry_prompt)
        retry_text = retry_response.text or ""
        retry_parsed, retry_err = clean_and_parse_json(retry_text)
        if retry_parsed is not None:
            return retry_parsed
        # If retry also fails, return fallback object with raw text
        return {
            "is_lab_report": True,
            "readable": False,
            "report_date": None,
            "results": [],
            "urgent_attention": False,
            "urgent_reason": None,
            "questions_for_doctor": [],
            "summary": "We had difficulty organizing the response into our standard table format.",
            "raw_text": retry_text or raw_text,
            "parse_fallback": True
        }
    except AnalyzerError:
        raise
    except Exception as fallback_e:
        return {
            "is_lab_report": True,
            "readable": False,
            "report_date": None,
            "results": [],
            "urgent_attention": False,
            "urgent_reason": None,
            "questions_for_doctor": [],
            "summary": "We had difficulty organizing the response into our standard table format.",
            "raw_text": raw_text,
            "parse_fallback": True
        }
