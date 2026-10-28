from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "sample_docs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

samples = {
    "claim-discharge-summary.txt": """Hospital discharge summary\nPatient: Asha Reddy\nDiagnosis: Planned hysterectomy\nDischarge date: 2026-09-14\nTreatment notes: Operation completed; patient stable and discharged with medication instructions.\n""",
    "invoice.txt": """Hospital invoice\nPatient: Asha Reddy\nProcedure: Hysterectomy\nNet payable: INR 1,52,000\nInsurance coverage applied: INR 1,35,000\n""",
    "garage-estimate.txt": """Garage estimate\nVehicle: Hyundai Creta\nRepair estimate: INR 82,500\nParts replaced: bumper, suspension, paint\nStatus: estimate filed and under approval\n""",
}

for name, content in samples.items():
    (OUT_DIR / name).write_text(content, encoding="utf-8")

print(f"Created {len(samples)} sample documents in {OUT_DIR}")
