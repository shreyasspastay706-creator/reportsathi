# Product Scope & Core Flow: ReportSathi

## 1. The Single Core Flow

```
[Patient / Caregiver Uploads Lab PDF or Photo]
                     │
                     ▼
[In-Memory Text & Table Extraction + Visual Fallback]
                     │
                     ▼
[Grounding & Verification Gate: Side-by-Side Table of Extracted Numbers vs Paper]
                     │
                     ▼
[Plain-Language Bilingual Translation (English / Spoken Kannada)]
                     │
                     ▼
[Critical Panic-Value Triage (Red Emergency Banner if Life-Threatening)]
                     │
                     ▼
[Summary + 3 Doctor Discussion Questions + Mandatory Non-Diagnostic Disclaimer]
```

**Value Proposition of the Flow:**
A patient holding a confusing lab report gets an immediate, plain-language translation of what their tests measure in their native language (English or Kannada), double-checks the extracted digits against their paper report to avoid OCR errors, and receives 2–3 concrete questions for their doctor—without ever being diagnosed, sold pills, or having their medical data stored.

---

## 2. Feature & Sub-Feature Breakdown

### A. Document Input & Processing
- **A1. Multi-format uploader:** Support PDF, JPG, PNG up to 10 MB.
- **A2. Hybrid extraction engine:** Fast text extraction for digital PDFs; automated 150 DPI rendering + multimodal vision fallback for scanned/photo reports.
- **A3. Ephemeral memory processing:** Zero persistent disk writes, zero report logging, zero database retention.

### B. Verification & Data Grounding
- **B1. Extracted values verification table:** Displays exact test name, observed value, unit, and printed reference range with a warning: *"Check these against your paper report before reading explanations."*
- **B2. Strict range binding:** Flags ("normal", "high", "low", "unknown") calculated strictly from printed laboratory ranges; ranges are never guessed.

### C. Bilingual Plain-Language Explanations
- **C1. Bilingual language toggle:** English (simple) and Kannada (conversational spoken Kannada).
- **C2. Test explanation cards:** Explains the physiological role of the biomarker in everyday words (e.g., *"Hemoglobin is like a delivery van carrying oxygen in your blood"*).
- **C3. Bracketed terminology for Kannada:** Retains English clinical test names in parentheses (e.g., `ಹಿಮೋಗ್ಲೋಬಿನ್ (Hemoglobin)`).
- **C4. Hedged contextual notes:** Carefully hedged explanations of what elevated/lowered results typically indicate without diagnostic labeling.

### D. Safety, Triage & Doctor Alignment
- **D1. Urgent attention red banner:** Triggers only on critical panic thresholds (e.g., critical glucose < 40 mg/dL, potassium > 6.5 mEq/L, severe thrombocytopenia) with emergency instruction (`Call 112 / Visit nearest hospital`).
- **D2. Doctor consultation questions:** Generates 2–3 grounded, personalized questions for the patient's next clinical visit.
- **D3. Persistent legal disclaimer:** Non-diagnostic educational notice pinned across all views.

---

## 3. Scope Categorization: MVP, Later, and Never

| Category | Feature / Sub-Feature | Strategic Rationale & Challenging |
|:---|:---|:---|
| **MVP** | **Multi-Format In-Memory Upload (PDF / JPG / PNG)** | **Core necessity.** Indian patients receive both WhatsApp PDFs and physical paper printouts. Without photo input, half the target audience is locked out. |
| **MVP** | **Hybrid Text + Vision Extraction** | **Core necessity.** Digital PDFs parse instantly; scanned images need vision OCR. |
| **MVP** | **Side-by-Side Paper Verification Table** | **Core necessity.** OCR on crumpled paper can misread decimals (9.8 vs 98). This table is the clinical and legal shield preventing harmful misinterpretation. |
| **MVP** | **Bilingual Translation (English & Spoken Kannada)** | **Core differentiator.** English-only is already commoditized by ChatGPT. Spoken Kannada with bracketed English test names directly solves the regional pain point. |
| **MVP** | **Strict Printed-Range Binding (No Range Guessing)** | **Core safety.** Normal ranges vary across labs and reagent kits. If no range is printed, the flag MUST be "unknown". |
| **MVP** | **Hedged Plain-Language Explanation Cards** | **Core value.** Explaining what the biomarker measures in simple terms without diagnostic leaps. |
| **MVP** | **Critical Panic-Value Alert Banner (112 Emergency)** | **Core safety.** Immediate duty-of-care notice if a parameter indicates life-threatening risk. |
| **MVP** | **2–3 Doctor Discussion Questions** | **Core value.** Channels anxiety into constructive doctor engagement. |
| **MVP** | **Mandatory Non-Diagnostic Disclaimer** | **Legal compliance.** Protects against unauthorized practice of medicine under Indian NMC Act & CDSCO guidelines. |
| **MVP** | **Ephemeral Processing (No Storage / No Accounts)** | **Challenged & Kept.** Having zero user accounts or databases eliminates 95% of DPDP Act 2023 compliance overhead and removes security liabilities. |

---

### What Was Challenged and Excluded from MVP (Moved to "Later" or "Never"):
1. **Prescription Interpretation (Excluded from MVP):** 
   - *Why challenged:* Handwritten doctor prescriptions in India have erratic cursive handwriting, complex dosage shorthand (e.g., TDS, BD, PC), and drug name ambiguity. A misread digit in a medication dose causes immediate pharmacological poisoning. Prescriptions are excluded from MVP.
2. **User Login & Accounts (Excluded from MVP):**
   - *Why challenged:* Adds onboarding friction and triggers rigorous data fiduciary obligations under DPDP Act 2023. The core comprehension flow works perfectly in an anonymous, ephemeral session.
3. **Audio Voiceover / TTS (Excluded from MVP):**
   - *Why challenged:* While valuable for illiterate elders, building natural spoken Kannada TTS adds latency and vendor cost. In MVP, family caregivers read the text cards.

---

### Features for "Later" (Phase 2 & B2B Expansion)
- **WhatsApp Business API Integration:** Delivering explanations directly within WhatsApp chat threads so users don't have to visit a web app.
- **Kannada Voice Readout (TTS):** Audio explanation player for elderly or semi-literate patients who prefer listening.
- **Longitudinal Trend Graphs:** Tracking 3+ historical reports for chronic diabetics (e.g., HbA1c trajectory), implemented via encrypted local storage.
- **Direct Lab LIS API Integration (B2B):** Ingesting structured laboratory JSON directly from lab software (eliminating OCR entirely).
- **Additional Indian Vernaculars:** Hindi, Tamil, Telugu, and Marathi language packs.

---

### Features in "Never" (Strict Red Lines)

| "Never" Feature | Legal & Clinical Reason |
|:---|:---|
| **Disease Diagnosis ("You have X disease")** | **Illegal & Dangerous.** Violates CDSCO Medical Device Rules (triggers SaMD Class C/D regulation) and Section 34 of National Medical Commission (NMC) Act. Only a licensed physician can diagnose. |
| **Drug / Dosage Recommendations ("Take 500mg Metformin")** | **Illegal & Fatal.** Recommending, starting, stopping, or altering prescription medications without a license is a criminal offense and risks lethal drug interactions. |
| **Home Remedies for Abnormal Results ("Drink bitter gourd juice")** | **Clinical Hazard.** Encourages patients to substitute unverified folk treatments for critical clinical care, directly causing treatment delays. |
| **Guessing Unprinted Reference Ranges** | **Diagnostic Drift.** Biological reference ranges depend on specific lab assay methods, reagent manufacturers, age, and sex. Guessing creates false reassurance or false alarm. |
| **Prescription Brand Substitution / E-Commerce Upselling** | **Conflict of Interest.** Pushing generic drug switches destroys trust and replicates the predatory behavior of existing pharmacy apps. |
| **Persistent Health Record Storage on Public Servers** | **Privacy Liability.** Retaining unencrypted health data creates severe data breach liabilities under India's DPDP Act 2023 (penalties up to ₹250 Cr). |
