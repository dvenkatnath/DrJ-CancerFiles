"""
Fixtures for scripts/benchmark_models.py.

10 synthetic clinical documents (for the extraction-model comparison) and 10
synthetic patient questions with a retrieved-context passage (for the
chat-model comparison), each hand-labeled with a small set of expected
keywords. The benchmark script checks whether a candidate model's output
mentions each expected keyword and reports that as a coverage score --

    coverage = (# expected keywords found in the model's output) / (# expected keywords)

That is a cheap automatic PROXY for extraction accuracy / answer quality, not
a substitute for clinical review. It's good for quickly ranking candidate
models and catching obvious regressions (a model that ignores the prompt, or
one that's way slower for no quality gain); it is NOT good at judging nuance,
so scripts/benchmark_models.py also saves every raw response to a transcript
file for a human to spot-check before trusting the ranking.

All text below is entirely synthetic -- no real patient data -- so this file
and everything it feeds is safe to run against any deployment target,
including the Railway PoC (synthetic-data-only) target.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractionFixture:
    id: str
    doc_type: str
    text: str
    expected_keywords: list[str]  # matched case-insensitively against the flattened extracted fact text


@dataclass
class ChatFixture:
    id: str
    question: str
    context: str  # stands in for a RAG-retrieved wiki+chunk context block
    expected_keywords: list[str] = field(default_factory=list)


EXTRACTION_FIXTURES: list[ExtractionFixture] = [
    ExtractionFixture(
        id="visit_note_allergy_med",
        doc_type="Oncology Visit Note",
        text=(
            "Oncology Follow-up Visit Note\nPatient: Test Patient A | MRN: BENCH-001\n"
            "Visit date: 12 Feb 2025\n\nReason for visit: Routine follow-up, Stage IIB invasive "
            "ductal carcinoma, post lumpectomy and adjuvant radiation (completed Nov 2024).\n\n"
            "Allergies: Sulfa drugs (hives).\n\nCurrent medications: Anastrozole 1mg daily.\n\n"
            "Assessment: Patient tolerating anastrozole well, mild joint stiffness reported.\n"
            "Plan: Continue anastrozole. Repeat mammogram in 6 months."
        ),
        expected_keywords=["sulfa", "anastrozole"],
    ),
    ExtractionFixture(
        id="lab_report_ca125",
        doc_type="Lab - CBC/Blood",
        text=(
            "Laboratory Report\nPatient: Test Patient A | MRN: BENCH-001\nCollected: 14 Feb 2025\n\n"
            "Test                Result      Unit      Reference Range\n"
            "CA-125               31.6        U/mL      0-35\n"
            "Hemoglobin           12.4        g/dL      12.0-15.5\n"
            "WBC                  6.1         /uL x10^3 4.0-11.0\n"
        ),
        expected_keywords=["ca-125", "31.6", "hemoglobin"],
    ),
    ExtractionFixture(
        id="discharge_summary_surgery",
        doc_type="Discharge Summary",
        text=(
            "Discharge Summary\nPatient: Test Patient B | MRN: BENCH-002\nAdmission: 02 Jan 2025 "
            "Discharge: 06 Jan 2025\nProcedure: Laparoscopic cholecystectomy converted to open due to "
            "adhesions.\nDischarge condition: Stable, tolerating regular diet.\nDischarge medications: "
            "Oxycodone 5mg PRN pain, Docusate 100mg BID.\nFollow-up: Surgery clinic in 2 weeks."
        ),
        expected_keywords=["cholecystectomy", "oxycodone"],
    ),
    ExtractionFixture(
        id="imaging_ct_finding",
        doc_type="Imaging",
        text=(
            "Imaging Report -- CT Abdomen/Pelvis with contrast\nPatient: Test Patient B | MRN: BENCH-002\n"
            "Exam date: 20 Jan 2025\n\nFindings: Stable 1.2 cm hypodense lesion in segment VI of the "
            "liver, unchanged from prior study, favor benign cyst. No new lesions. No lymphadenopathy.\n"
            "Impression: No evidence of disease progression."
        ),
        expected_keywords=["liver", "cyst", "no evidence"],
    ),
    ExtractionFixture(
        id="pathology_biopsy",
        doc_type="Pathology/Biopsy",
        text=(
            "Surgical Pathology Report\nPatient: Test Patient C | MRN: BENCH-003\nSpecimen: Core needle "
            "biopsy, left breast, 2 o'clock position.\nDiagnosis: Invasive ductal carcinoma, grade 2, "
            "ER+/PR+/HER2-negative. Ki-67 index approximately 18%."
        ),
        expected_keywords=["invasive ductal carcinoma", "her2-negative", "ki-67"],
    ),
    ExtractionFixture(
        id="genomic_report",
        doc_type="Genomic/Molecular",
        text=(
            "Molecular Tumor Profiling Report\nPatient: Test Patient C | MRN: BENCH-003\n"
            "Pathogenic variant detected: BRCA2 c.5946delT (p.Ser1982fs).\nVariant of uncertain "
            "significance: PALB2 c.2323C>T.\nNo actionable alterations otherwise identified."
        ),
        expected_keywords=["brca2", "palb2"],
    ),
    ExtractionFixture(
        id="prescription_note",
        doc_type="Prescription",
        text=(
            "Prescription / Treatment Note\nPatient: Test Patient D | MRN: BENCH-004\nDate: 03 Mar 2025\n"
            "Start: Pembrolizumab 200mg IV every 3 weeks for recurrent disease.\nPre-medication: "
            "Diphenhydramine 25mg IV, Acetaminophen 650mg PO.\nBaseline labs reviewed and acceptable."
        ),
        expected_keywords=["pembrolizumab", "diphenhydramine"],
    ),
    ExtractionFixture(
        id="new_patient_consult",
        doc_type="Case Summary/Advice Note",
        text=(
            "New Patient Oncology Consult\nPatient: Test Patient D | MRN: BENCH-004\nDate: 15 Jan 2025\n"
            "History: 58F with newly diagnosed Stage IV colorectal adenocarcinoma, liver metastases.\n"
            "Plan: Start FOLFOX plus bevacizumab. Discussed goals of care and clinical trial eligibility."
        ),
        expected_keywords=["colorectal", "folfox", "bevacizumab"],
    ),
    ExtractionFixture(
        id="lab_report_cbc_only",
        doc_type="Lab - CBC/Blood",
        text=(
            "Laboratory Report\nPatient: Test Patient E | MRN: BENCH-005\nCollected: 28 Feb 2025\n\n"
            "Test                Result      Unit      Reference Range\n"
            "Hemoglobin           9.8         g/dL      12.0-15.5\n"
            "Platelets            98          /uL x10^3 150-400\n"
            "ANC                  1.1         /uL x10^3 1.5-8.0\n"
        ),
        expected_keywords=["hemoglobin", "platelets", "anc"],
    ),
    ExtractionFixture(
        id="visit_note_no_findings",
        doc_type="Oncology Visit Note",
        text=(
            "Oncology Follow-up Visit Note\nPatient: Test Patient E | MRN: BENCH-005\nVisit date: 03 Mar "
            "2025\n\nReason for visit: Surveillance visit, no evidence of disease x 18 months.\n"
            "No new complaints. No allergies. Not currently on any medications.\n"
            "Plan: Continue surveillance imaging annually. Return in 12 months."
        ),
        expected_keywords=["no evidence of disease", "surveillance"],
    ),
]


CHAT_FIXTURES: list[ChatFixture] = [
    ChatFixture(
        id="allergy_lookup",
        question="Any documented allergies?",
        context="Wiki - Allergies: Sulfa drugs (hives), reported 12 Feb 2025.",
        expected_keywords=["sulfa"],
    ),
    ChatFixture(
        id="latest_lab_value",
        question="What is the latest CA-125 value?",
        context="Wiki - Lab Highlights: CA-125 31.6 U/mL on 2025-02-14 (reference range 0-35, within normal limits).",
        expected_keywords=["31.6"],
    ),
    ChatFixture(
        id="current_meds",
        question="What medications is the patient currently on?",
        context="Wiki - Medications: Anastrozole 1mg daily, started Nov 2024 post-radiation.",
        expected_keywords=["anastrozole"],
    ),
    ChatFixture(
        id="diagnosis_summary",
        question="What is this patient's primary diagnosis?",
        context="Wiki - Problem List: Stage IIB invasive ductal carcinoma, left breast, ER+/PR+/HER2-negative.",
        expected_keywords=["invasive ductal carcinoma"],
    ),
    ChatFixture(
        id="last_imaging_result",
        question="What did the most recent imaging show?",
        context="Wiki - Visit Timeline: CT Abdomen/Pelvis 2025-01-20 -- stable 1.2cm hepatic cyst, no evidence of progression.",
        expected_keywords=["no evidence", "cyst"],
    ),
    ChatFixture(
        id="genomic_variant",
        question="Were any actionable genomic variants found?",
        context="Wiki - Notes: Genomic panel -- pathogenic BRCA2 c.5946delT detected; PALB2 VUS; no other actionable alterations.",
        expected_keywords=["brca2"],
    ),
    ChatFixture(
        id="treatment_plan",
        question="What is the current treatment plan?",
        context="Wiki - Care Plan: FOLFOX plus bevacizumab, cycle 3 of 12, started 2025-01-22.",
        expected_keywords=["folfox", "bevacizumab"],
    ),
    ChatFixture(
        id="surgical_history",
        question="What surgeries has this patient had?",
        context="Wiki - Visit Timeline: Laparoscopic cholecystectomy converted to open, 2025-01-04, discharged stable.",
        expected_keywords=["cholecystectomy"],
    ),
    ChatFixture(
        id="counts_trend",
        question="Are the blood counts concerning right now?",
        context="Wiki - Lab Highlights: Hemoglobin 9.8 g/dL (low), Platelets 98 (low), ANC 1.1 (low), collected 2025-02-28.",
        expected_keywords=["hemoglobin", "low"],
    ),
    ChatFixture(
        id="disease_status",
        question="Is there any evidence of disease recurrence?",
        context="Wiki - Notes: Surveillance visit 2025-03-03 -- no evidence of disease x 18 months, no new complaints.",
        expected_keywords=["no evidence of disease"],
    ),
]
