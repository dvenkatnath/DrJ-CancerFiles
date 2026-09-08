"""
Entirely synthetic clinical text for seed/demo patients. No real patient data
anywhere in this file or anything it touches -- safe for the Railway PoC
(synthetic-data-only) deployment target as well as local dev demos.
"""

MARIA_VISIT_NOTE = """Oncology Follow-up Visit Note
Patient: Maria Alvarez | MRN: DEMO-1001 | DOB: 1968-03-14
Visit date: 10 Jan 2024

Reason for visit: Routine follow-up, Stage IIIC high-grade serous ovarian carcinoma,
post cytoreductive surgery and adjuvant chemotherapy (completed Aug 2023).

Allergies: Penicillin (rash).

Current medications: Letrozole 2.5mg daily, Ondansetron 8mg PRN nausea.

Problem list:
1. High-grade serous ovarian carcinoma, Stage IIIC, in remission since Sep 2023.
2. Chemotherapy-induced peripheral neuropathy, grade 1, improving.
3. Hypothyroidism, on levothyroxine.

Assessment: Patient doing well, no new symptoms. CA-125 trending down since last visit.
Neuropathy in fingertips continuing to improve, no longer affecting fine motor tasks.

Plan: Continue letrozole. Repeat CA-125 and CBC in 6 weeks. Follow-up visit in 3 months.
Counseled on signs/symptoms of recurrence to report immediately.
"""

MARIA_LAB_REPORT = """Laboratory Report
Patient: Maria Alvarez | MRN: DEMO-1001
Collected: 15 Feb 2024

Test                Result      Unit      Reference Range
CA-125               22.4        U/mL      0-35
Hemoglobin           11.8        g/dL      12.0-15.5
WBC                  5.2         /uL x10^3 4.0-11.0
Platelets            210         /uL x10^3 150-400
Creatinine           0.8         mg/dL     0.6-1.1

Interpretation: CA-125 within normal limits, consistent with continued remission.
Mild anemia, stable compared to prior draw, attributed to prior chemotherapy.
"""

MARIA_DISCHARGE_SUMMARY = """Discharge Summary
Patient: Maria Alvarez | MRN: DEMO-1001
Admission: 28 Aug 2023  Discharge: 02 Sep 2023

Procedure: Exploratory laparotomy, total abdominal hysterectomy, bilateral
salpingo-oophorectomy, omentectomy, cytoreductive surgery for ovarian carcinoma.

Hospital course: Uneventful post-operative recovery. Ambulating by post-op day 2.
Pain controlled with oral analgesics by discharge. No signs of infection.

Discharge medications: Acetaminophen 500mg PRN pain, Docusate 100mg BID.

Follow-up plan: Oncology follow-up in 2 weeks to discuss pathology and adjuvant
chemotherapy plan. Wound check with surgeon in 10 days.
"""

JAMES_VISIT_NOTE = """Oncology Follow-up Visit Note
Patient: James Whitfield | MRN: DEMO-1002 | DOB: 1955-11-02
Visit date: 05 Nov 2023

Reason for visit: Surveillance visit, Stage II colorectal adenocarcinoma, post
resection and adjuvant FOLFOX, treatment completed Jun 2023.

Allergies: No known drug allergies.

Current medications: Multivitamin daily.

Problem list:
1. Colorectal adenocarcinoma, Stage II, s/p right hemicolectomy + adjuvant FOLFOX, in remission.
2. Peripheral neuropathy from oxaliplatin, grade 1, stable.
3. Hypertension, well controlled on lisinopril.

Assessment: No evidence of disease on surveillance CT. CEA within normal limits.
Patient reports good energy, tolerating residual neuropathy well.

Plan: Continue surveillance per NCCN guidelines -- CEA every 3-6 months, CT chest/
abdomen/pelvis annually, colonoscopy in 1 year. Next visit in 6 months.
"""

JAMES_LAB_REPORT = """Laboratory Report
Patient: James Whitfield | MRN: DEMO-1002
Collected: 02 Nov 2023

Test                Result      Unit      Reference Range
CEA                  2.1         ng/mL     0-3.0
Hemoglobin           13.9        g/dL      13.5-17.5
WBC                  6.1         /uL x10^3 4.0-11.0
Platelets            245         /uL x10^3 150-400

Interpretation: CEA within normal limits, no biochemical evidence of recurrence.
Blood counts normal.
"""

# Two more time points for James so the Lab Trends panel (app/services/trends.py)
# has a real multi-document series to plot out of the box, rather than a
# single point -- one from just after his FOLFOX finished (CEA still settling)
# and one from his most recent surveillance visit (fully normalized).
JAMES_LAB_REPORT_EARLY = """Laboratory Report
Patient: James Whitfield | MRN: DEMO-1002
Collected: 10 Jul 2023

Test                Result      Unit      Reference Range
CEA                  4.2         ng/mL     0-3.0
Hemoglobin           12.8        g/dL      13.5-17.5
WBC                  5.4         /uL x10^3 4.0-11.0
Platelets            238         /uL x10^3 150-400

Interpretation: CEA modestly elevated, ~1 month post-FOLFOX; recommend recheck at next
visit rather than immediate re-staging. Mild anemia consistent with recent chemotherapy.
"""

JAMES_LAB_REPORT_LATEST = """Laboratory Report
Patient: James Whitfield | MRN: DEMO-1002
Collected: 20 Apr 2024

Test                Result      Unit      Reference Range
CEA                  1.8         ng/mL     0-3.0
Hemoglobin           14.2        g/dL      13.5-17.5
WBC                  6.4         /uL x10^3 4.0-11.0
Platelets            251         /uL x10^3 150-400

Interpretation: CEA normalized and trending down across surveillance visits. Blood
counts fully recovered. No biochemical evidence of recurrence.
"""

PRIYA_VISIT_NOTE = """Oncology Visit Note
Patient: Priya Nair | MRN: DEMO-1003 | DOB: 1979-07-22
Visit date: 22 Jul 2024

Reason for visit: New patient consult, newly diagnosed Stage IV non-small cell
lung cancer (adenocarcinoma), EGFR exon 19 deletion positive.

Allergies: Sulfa drugs (hives), Shellfish (anaphylaxis -- carries EpiPen).

Current medications: Osimertinib 80mg daily (started this visit), Albuterol
inhaler PRN.

Problem list:
1. Non-small cell lung cancer, Stage IV, EGFR exon 19 deletion positive, newly diagnosed.
2. Mild persistent asthma.

Assessment: Patient recently diagnosed after presenting with persistent cough
and unintentional weight loss. Staging CT and brain MRI show pulmonary primary
with liver metastases, no CNS involvement. Molecular testing confirms EGFR
exon 19 deletion -- candidate for first-line osimertinib.

Plan: Start osimertinib 80mg daily. Baseline EKG for QTc prior to starting.
Follow-up in 4 weeks with restaging CT at 8 weeks. Discussed side effect
profile including rash, diarrhea, and rare but serious ILD risk -- to call
immediately for new/worsening shortness of breath.
"""

PRIYA_IMAGING_REPORT = """Imaging Report -- CT Chest/Abdomen/Pelvis with contrast
Patient: Priya Nair | MRN: DEMO-1003
Study date: 15 Jul 2024

Findings: 3.8cm spiculated mass in the right upper lobe, unchanged in appearance
from outside imaging. Two hepatic lesions, largest 2.1cm in segment VI, new
since no prior liver imaging available for comparison -- consistent with
metastatic disease given clinical context. No pathologic lymphadenopathy.
No pleural effusion.

Impression: Right upper lobe mass with hepatic metastases, consistent with
Stage IV NSCLC as clinically diagnosed. Recommend correlation with molecular
pathology and oncology consultation for systemic therapy planning.
"""

SEED_PATIENTS = [
    {
        "mrn": "DEMO-1001",
        "name": "Maria Alvarez",
        "date_of_birth": "1968-03-14",
        "sex": "female",
        "documents": [
            ("Oncology Visit Note - 2024-01-10.txt", MARIA_VISIT_NOTE),
            ("CA-125 Lab Report - 2024-02-15.txt", MARIA_LAB_REPORT),
            ("Discharge Summary - 2023-09-02.txt", MARIA_DISCHARGE_SUMMARY),
        ],
        "auto_publish": False,
    },
    {
        "mrn": "DEMO-1002",
        "name": "James Whitfield",
        "date_of_birth": "1955-11-02",
        "sex": "male",
        "documents": [
            ("Oncology Visit Note - 2023-11-05.txt", JAMES_VISIT_NOTE),
            ("CEA Lab Report - 2023-07-10.txt", JAMES_LAB_REPORT_EARLY),
            ("CEA Lab Report - 2023-11-02.txt", JAMES_LAB_REPORT),
            ("CEA Lab Report - 2024-04-20.txt", JAMES_LAB_REPORT_LATEST),
        ],
        "auto_publish": True,
    },
    {
        "mrn": "DEMO-1003",
        "name": "Priya Nair",
        "date_of_birth": "1979-07-22",
        "sex": "female",
        "documents": [
            ("New Patient Consult - 2024-07-22.txt", PRIYA_VISIT_NOTE),
            ("CT Chest Abdomen Pelvis - 2024-07-15.txt", PRIYA_IMAGING_REPORT),
        ],
        "auto_publish": False,
    },
]
