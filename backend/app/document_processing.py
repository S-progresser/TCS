from __future__ import annotations

import json
import re
from typing import Any, Awaitable, Callable, Literal

import pymupdf
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError

from backend.app.agents.document_analyst import DocumentAnalyst
from backend.app.config import get_settings
from backend.app.llm import get_llm_client
from backend.app.orchestrator import calculate_readiness
from backend.app.retriever import load_rulebooks
from backend.app.schemas import DocumentReview, PolicyRule

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class ExtractionResult(BaseModel):
    status: Literal["extracted", "unreadable", "unsupported"]
    text: str = Field(default="", exclude=True)
    document_type: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    message: str | None = None
    provider: str = "deterministic"


class VisionExtraction(BaseModel):
    text: str = ""


class ActionDraft(BaseModel):
    actions: list[str] = Field(default_factory=list)
    provider_message: str = ""


def safe_filename(value: str | None) -> str:
    raw = (value or "document").replace("\\", "/").split("/")[-1]
    cleaned = "".join(char for char in raw if char.isalnum() or char in " ._-()").strip(" .")
    return cleaned[:160] or "document"


def detected_content_type(filename: str, content: bytes) -> tuple[str, str]:
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if content.startswith(b"%PDF-") and extension == "pdf":
        return "application/pdf", "document"
    if content.startswith(b"\x89PNG\r\n\x1a\n") and extension == "png":
        return "image/png", "image"
    if content.startswith(b"\xff\xd8\xff") and extension in {"jpg", "jpeg"}:
        return "image/jpeg", "image"
    raise ValueError("File extension and file contents do not match a supported PDF, JPG, JPEG, or PNG.")


def _extract_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    patterns = {
        "claimant_name": r"(?:patient|claimant|member|insured|name)\s*[:\-]\s*([^\r\n,]{2,80})",
        "provider_name": r"(?:hospital|garage|provider)\s*(?:name)?\s*[:\-]\s*([^\r\n,]{2,100})",
        "date": r"(?:treatment date|date of treatment|date of service|invoice date|bill date|date)\s*[:\-]\s*([0-9]{1,4}[./\-][0-9]{1,2}[./\-][0-9]{1,4})",
        "amount": r"(?:grand total|total amount|bill amount|invoice amount|total|amount)\s*[:\-]?\s*(?:₹|INR|Rs\.?)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        "vehicle_registration": r"(?:vehicle registration|registration number|registration no\.?|vehicle reg(?:istration)?)\s*[:\-]\s*([A-Z0-9\- ]{5,20})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            fields[key] = match.group(1).strip()

    item_lines = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"(?:₹|INR|Rs\.?)\s*[0-9]|(?:medicine|consultation|room charge|surgery|repair|labour|parts)\b", line, re.I)
    ]
    if item_lines:
        fields["itemized_charges"] = " | ".join(item_lines[:20])
    if re.search(r"\b(?:signed|signature)\b", text, re.I):
        fields["signature_indicator"] = "Signature mentioned in extracted text"
    elif re.search(r"\b(?:unsigned|without signature|not signed)\b", text, re.I):
        fields["signature_indicator"] = "Document states it is unsigned"
    if re.search(r"\b(?:stamp|stamped|seal)\b", text, re.I):
        fields["stamp_indicator"] = "Stamp or seal mentioned in extracted text"
    return fields


def _document_type(text: str, content_kind: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("discharge summary", "discharge certificate", "discharge report")):
        return "discharge_summary"
    if any(token in lowered for token in ("garage estimate", "repair estimate", "cost estimate")):
        return "garage_estimate"
    if any(token in lowered for token in ("final invoice", "hospital invoice", "medical bill", "hospital bill")):
        return "invoice"
    if content_kind == "image":
        return "claim_document_image"
    return "claim_document"


async def extract_document(filename: str, content: bytes, mime_type: str, content_kind: str) -> ExtractionResult:
    if mime_type == "application/pdf":
        try:
            with pymupdf.open(stream=content, filetype="pdf") as document:
                text = "\n".join(page.get_text("text") for page in document).strip()
        except (pymupdf.FileDataError, pymupdf.EmptyFileError, ValueError, RuntimeError):
            return ExtractionResult(status="unreadable", message="This PDF is corrupt, encrypted, or could not be opened.")
        if len(text) < 20:
            return ExtractionResult(
                status="unreadable",
                message="This PDF has too little selectable text to read. It may be a scanned document; OCR is not available for PDFs in this demo.",
            )
        return ExtractionResult(
            status="extracted",
            text=text[:100_000],
            document_type=_document_type(text, content_kind),
            fields=_extract_fields(text),
        )

    try:
        from io import BytesIO

        with Image.open(BytesIO(content)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return ExtractionResult(status="unreadable", message="The image is corrupt or cannot be decoded.")

    vision = await get_llm_client().inspect_image(
        content,
        mime_type,
        "Read only text that is visibly present in this insurance claim document. Return JSON with one string field named text. Do not infer missing values.",
    )
    if vision.provider != "groq":
        return ExtractionResult(
            status="unreadable",
            message="Image text could not be read because Groq vision is unavailable. Configure GROQ_API_KEY or upload a text-based PDF.",
            provider=vision.provider,
        )
    try:
        parsed = VisionExtraction.model_validate_json(vision.content)
    except ValidationError:
        return ExtractionResult(
            status="unreadable",
            message="The image reader returned an invalid extraction response. Please upload a clearer image.",
            provider="groq",
        )
    text = parsed.text.strip()
    if len(text) < 10:
        return ExtractionResult(status="unreadable", message="No readable claim-document text was found in the image.", provider="groq")
    return ExtractionResult(
        status="extracted",
        text=text[:100_000],
        document_type=_document_type(text, content_kind),
        fields=_extract_fields(text),
        provider="groq",
    )


def _rulebook_for_claim(claim: dict[str, Any]) -> PolicyRule:
    rules = load_rulebooks()
    product = str(claim.get("product", "")).lower()
    category = "motor" if "motor" in product else "documents"
    return next((rule for rule in rules if rule.category == category), rules[0])


def _normalize(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _document_satisfies_requirement(requirement: str, doc_type: str, text: str) -> bool:
    req = requirement.lower()
    lowered = text.lower()
    if "invoice" in req or "bill" in req:
        return doc_type == "invoice" or ("invoice" in lowered and "final" in lowered) or "hospital bill" in lowered or "medical bill" in lowered
    if "discharge" in req:
        return doc_type == "discharge_summary" or ("discharge" in lowered and ("summary" in lowered or "certificate" in lowered or "report" in lowered))
    if "estimate" in req:
        return doc_type == "garage_estimate" or "garage estimate" in lowered
    if "photo" in req:
        return doc_type == "vehicle_damage_photos"
    return False


def _validate_document(
    *,
    filename: str,
    extraction: ExtractionResult,
    claim: dict[str, Any],
    rule: PolicyRule,
) -> DocumentReview:
    if extraction.status != "extracted":
        return DocumentReview(
            filename=filename,
            valid=False,
            score=None,
            claim_id=claim["id"],
            extraction_status=extraction.status,
            extraction_message=extraction.message,
            extracted_document_type=extraction.document_type,
            fields_unverified=["Document contents"],
            next_steps=["Upload a clearer, text-based copy or a supported image with readable text."],
            readiness_score=calculate_readiness(claim).readiness_score,
            provider=extraction.provider,
            replayed=get_settings().replay,
        )

    text = extraction.text
    doc_type = extraction.document_type or "claim_document"
    checklist = [str(item).lower() for item in claim.get("checklist", [])]
    missing: list[str] = []
    passed: list[str] = []
    mismatches: list[str] = []
    unverified: list[str] = []
    actions: list[str] = []

    for requirement in rule.required_documents:
        checklist_match = any(requirement.lower().split()[0] in item for item in checklist)
        current_file_match = _document_satisfies_requirement(requirement, doc_type, text)
        if checklist_match or current_file_match:
            passed.append(f"{requirement} is present in the claim checklist or uploaded file.")
        else:
            missing.append(requirement)
            actions.append(f"Upload the {requirement.lower()}.")

    fields = extraction.fields
    expected_name = str(claim.get("customer_name", "")).strip()
    actual_name = fields.get("claimant_name")
    if actual_name:
        if _normalize(expected_name) != _normalize(actual_name):
            mismatches.append(f"Claimant name in document ({actual_name}) does not match the claim record ({expected_name}).")
        else:
            passed.append("Claimant name matches the claim record.")
    else:
        unverified.append("Claimant name could not be read from this document.")
    expected_amount = claim.get("claim_amount")
    amount = fields.get("amount")
    if amount and expected_amount is not None:
        try:
            numeric_amount = float(amount.replace(",", ""))
            if abs(numeric_amount - float(expected_amount)) > 0.01:
                mismatches.append(f"Document amount ₹{numeric_amount:,.2f} differs from the claim amount ₹{float(expected_amount):,.2f}.")
            else:
                passed.append("Document amount matches the claim amount.")
        except ValueError:
            unverified.append("Bill amount could not be interpreted.")
    else:
        unverified.append("Bill amount could not be verified from this document.")
    date_field = next((field for field in rule.required_fields if "date" in field.lower()), None)
    if date_field:
        extracted_date = fields.get("date")
        expected_date = claim.get("treatment_date") or claim.get("incident_date") or claim.get("date_of_service")
        if not extracted_date:
            unverified.append(f"{date_field.capitalize()} could not be read from this document.")
        elif expected_date:
            if _normalize(extracted_date) != _normalize(str(expected_date)):
                mismatches.append(f"Document date ({extracted_date}) does not match the claim record ({expected_date}).")
            else:
                passed.append(f"{date_field.capitalize()} matches the claim record.")
        else:
            passed.append(f"{date_field.capitalize()} ({extracted_date}) is present in the document.")
    if "vehicle registration" in [field.lower() for field in rule.required_fields] and "vehicle_registration" not in fields:
        unverified.append("Vehicle registration could not be read from this document.")
    if rule.itemization_required:
        if fields.get("itemized_charges"):
            passed.append("Itemized charges are visible in the extracted text.")
        elif doc_type == "invoice" or "invoice" in text.lower() or "bill" in text.lower():
            unverified.append("Itemized charges could not be verified from the extracted text.")
            actions.append("Ask the provider for a clearly itemized final invoice.")
    if rule.signature_required and re.search(r"\b(?:unsigned|without signature|not signed)\b", text, re.I):
        missing.append("A signed provider document")
        actions.append("Request a signed copy of the required provider document.")
    elif rule.signature_required and fields.get("signature_indicator"):
        passed.append("A signature indicator appears in the extracted text; the actual signature image was not verified.")
    elif rule.signature_required:
        unverified.append("A provider signature could not be verified from the extracted text.")

    if actual_name and _normalize(expected_name) != _normalize(actual_name):
        actions.append("Confirm the claimant name spelling with the provider.")
    if any("date" in item.lower() for item in unverified):
        actions.append("Confirm the treatment or incident date against the claim record.")
    if any("signature" in item.lower() for item in unverified):
        actions.append("Provide a copy where the provider signature can be clearly checked.")
    if unverified and not actions:
        actions.append("Upload a clearer copy so the listed document fields can be checked.")

    review = DocumentReview(
        filename=filename,
        valid=not missing and not mismatches and not unverified,
        score=None,
        missing_documents=list(dict.fromkeys(missing)),
        mismatches=list(dict.fromkeys(mismatches)),
        next_steps=list(dict.fromkeys(actions)),
        fields_missing=list(dict.fromkeys(missing)),
        fields_unverified=list(dict.fromkeys(unverified)),
        claim_id=claim["id"],
        extraction_status="extracted",
        extraction_message="Text was extracted from the uploaded file. Automated checks are demo guidance, not an approval decision.",
        extracted_fields=fields,
        checks_passed=passed,
        readiness_score=None,
        extracted_document_type=doc_type,
        provider=extraction.provider,
        replayed=get_settings().replay,
    )
    return review


async def analyze_upload(
    *,
    filename: str,
    content: bytes,
    mime_type: str,
    content_kind: str,
    claim: dict[str, Any],
    on_stage: Callable[..., Awaitable[None]],
) -> DocumentReview:
    session_file_type = "image" if content_kind == "image" else "document"
    await on_stage(stage="received", status="completed", message="Document received", details="The file is associated with the selected claim.", document_type=session_file_type)
    await on_stage(stage="reading", status="active", message="Reading document", details="Checking the file contents and extracting readable text.", document_type=session_file_type)
    extraction = await extract_document(filename, content, mime_type, content_kind)
    if extraction.status != "extracted":
        review = await DocumentAnalyst().validate_extracted_document(
            filename=filename, extraction=extraction, claim=claim, rulebook=_rulebook_for_claim(claim)
        )
        await on_stage(stage="reading", status="failed", message="Document could not be read", details=extraction.message or "No readable text was extracted.", document_type=session_file_type, error="unreadable_document")
        await on_stage(
            stage="reading",
            status="failed",
            message="Analysis stopped because extraction failed",
            details=extraction.message or "Upload a readable copy to continue.",
            document_type=session_file_type,
            event_type="document.failed",
            result=review.model_dump(),
            error="unreadable_document",
        )
        return review

    await on_stage(stage="reading", status="completed", message="Reading document", details="Readable document text was extracted.", document_type=session_file_type)
    await on_stage(stage="extracting", status="active", message="Extracting important details", details="Finding only fields explicitly present in the extracted text.", document_type=session_file_type)
    extraction.fields = _extract_fields(extraction.text)
    await on_stage(stage="extracting", status="completed", message="Extracting important details", details=f"{len(extraction.fields)} supported field(s) found; unreadable fields are not treated as missing.", document_type=session_file_type)

    rule = _rulebook_for_claim(claim)
    await on_stage(stage="requirements", status="active", message="Checking insurer requirements", details=f"Applying the configured {rule.category} demo rulebook.", document_type=session_file_type)
    review = await DocumentAnalyst().validate_extracted_document(
        filename=filename, extraction=extraction, claim=claim, rulebook=rule
    )
    await on_stage(stage="requirements", status="completed", message="Checking insurer requirements", details="Configured document requirements have been checked.", document_type=session_file_type)
    await on_stage(stage="claim_compare", status="active", message="Comparing with your claim", details="Comparing extracted values with the selected claim record.", document_type=session_file_type)
    await on_stage(stage="claim_compare", status="completed", message="Comparing with your claim", details="Available names and amounts were compared; unreadable fields remain unverified.", document_type=session_file_type)
    await on_stage(stage="explanation", status="active", message="Preparing your explanation", details="Preparing actions from the confirmed gaps and mismatches.", document_type=session_file_type)

    if review.next_steps:
        prompt = json.dumps({
            "task": "Rewrite only the supplied actions as a concise personalized action plan and draft a provider-facing request.",
            "claimant": claim.get("customer_name"),
            "claim_id": claim.get("id"),
            "confirmed_missing_items": review.missing_documents,
            "confirmed_mismatches": review.mismatches,
            "unverified_fields": review.fields_unverified,
            "allowed_actions": review.next_steps,
            "response_schema": {"actions": ["exact strings from allowed_actions"], "provider_message": "one concise request, no unsupported facts"},
        })
        draft_result = await get_llm_client().generate_result(prompt, model=get_llm_client().settings.fast_model, json_mode=True, max_tokens=300)
        if draft_result.provider == "groq":
            try:
                draft = ActionDraft.model_validate_json(draft_result.content)
                allowed = {action.casefold(): action for action in review.next_steps}
                if draft.actions and {action.casefold() for action in draft.actions} == set(allowed):
                    review.next_steps = list(dict.fromkeys(allowed[action.casefold()] for action in draft.actions))
                required_phrases = review.missing_documents or review.mismatches
                if draft.provider_message and all(item.casefold() in draft.provider_message.casefold() for item in required_phrases):
                    review.provider_message = draft.provider_message
                review.provider = "groq"
            except ValidationError:
                review.provider = "deterministic"
        else:
            if review.provider != "groq":
                review.provider = draft_result.provider
    if not review.provider_message:
        missing = ", ".join(review.missing_documents)
        if missing:
            review.provider_message = f"Hello, please provide {missing} for claim {claim['id']} so the insurer can continue its review."
        elif review.mismatches:
            review.provider_message = f"Hello, please confirm the document details for claim {claim['id']}: {review.mismatches[0]}"

    checklist_after_upload = list(claim.get("checklist", []))
    document_checklist_labels = {
        "discharge_summary": "Hospital discharge summary submitted",
        "invoice": "Final hospital invoice attached",
        "garage_estimate": "Garage estimate submitted",
    }
    if extraction.document_type in document_checklist_labels:
        checklist_after_upload.append(document_checklist_labels[extraction.document_type])
    if "discharge" in extraction.text.lower() and ("summary" in extraction.text.lower() or "certificate" in extraction.text.lower()):
        checklist_after_upload.append("Hospital discharge summary submitted")
    if "invoice" in extraction.text.lower() or "bill" in extraction.text.lower():
        checklist_after_upload.append("Final hospital invoice attached")
    if extraction.fields.get("amount"):
        checklist_after_upload.append("Treatment date and claim amount verified")
    claim_for_score = {**claim, "checklist": list(dict.fromkeys(checklist_after_upload))}
    review.readiness_score = calculate_readiness(claim_for_score).readiness_score
    if review.valid and review.score is None:
        review.score = 100
    review.replayed = get_settings().replay
    if review.replayed:
        review.provider = "replay"
    await on_stage(
        stage="explanation",
        status="completed",
        message="Preparing your explanation",
        details="The analysis findings and evidence-based next steps are ready.",
        document_type=session_file_type,
        event_type="document.completed",
        result=review.model_dump(),
    )
    return review


def rulebook_for_claim(claim: dict[str, Any]) -> PolicyRule:
    return _rulebook_for_claim(claim)
