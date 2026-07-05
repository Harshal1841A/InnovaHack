from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
import os
from typing import Dict, Any
import uuid
from dotenv import load_dotenv

load_dotenv()  # Load .env before any other imports that read env vars

import schemas
from database import init_db
from evidence import get_evidence_for_query

app = FastAPI(title="Aegis Backend (Harshal's Scope)")

# Allow CORS for local development and deployed frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def serve_frontend():
    if os.path.exists("frontend.html"):
        return FileResponse("frontend.html")
    return HTMLResponse("<h1>Aegis Backend Running</h1><p>frontend.html not found</p>")


@app.post("/upload")
def upload_document() -> Dict[str, str]:
    # Dummy implementation
    return {"document_id": f"doc_{uuid.uuid4().hex[:8]}"}

from llm import extract_document_fields, summarize_case as llm_summarize, draft_followup as llm_draft, reconstruct_field as llm_reconstruct, synthesize_case as llm_synthesize
from database import get_db

# ... skipping previous endpoints, I'll just do a targeted replace for the bottom of the file


@app.post("/extract", response_model=schemas.ExtractionSchema)
def extract_document(request: schemas.ExtractRequest) -> schemas.ExtractionSchema:
    fields = extract_document_fields(request.ocr_text)
    
    # Map back to FieldData models
    mapped_fields = {}
    for k, v in fields.items():
        mapped_fields[k] = schemas.FieldData(
            value=v.get("value", ""),
            confidence=v.get("confidence", 0.0),
            status=v.get("status", "not_found")
        )
        
    return schemas.ExtractionSchema(
        document_id=request.document_id,
        document_type="invoice", # Simplified for hackathon
        fields=mapped_fields
    )

@app.post("/validate", response_model=schemas.ValidationSchema)
def validate_case(request: schemas.ValidateRequest) -> schemas.ValidationSchema:
    # Mocks Harshit's validation output
    return schemas.ValidationSchema(
        case_id=request.case_id,
        amount_match=True,
        currency_match=True,
        date_consistent=False,
        vendor_match=True,
        purpose_code_plausible=True,
        purpose_code_note="Standard IT services",
        missing_fields=["tax_id"],
        flags=["Date differs from contract"]
    )

@app.post("/evidence", response_model=schemas.Evidence)
def get_evidence(request: schemas.EvidenceRequest) -> schemas.Evidence:
    # Uses Tavily API and LLM extraction
    return get_evidence_for_query(request.query, request.case_id)

@app.post("/summarize", response_model=schemas.SummaryOutput)
def summarize_case(request: schemas.SummarizeRequest) -> schemas.SummaryOutput:
    result = llm_summarize(request.validation.model_dump(), request.evidence.model_dump())
    return schemas.SummaryOutput(
        case_id=request.case_id,
        summary=result.get("summary", ""),
        recommendation=result.get("recommendation", "further_investigation_recommended")
    )

@app.post("/draft-followup", response_model=schemas.FollowupDraftOutput)
def draft_followup(request: schemas.FollowupDraftRequest) -> schemas.FollowupDraftOutput:
    result = llm_draft(request.validation.model_dump())
    return schemas.FollowupDraftOutput(
        case_id=request.case_id,
        trigger_reason=result.get("trigger_reason", "error"),
        drafted_message=result.get("drafted_message", "")
    )

@app.post("/reconstruct", response_model=schemas.ReconstructionOutput)
def reconstruct_field(request: schemas.ReconstructRequest) -> schemas.ReconstructionOutput:
    result = llm_reconstruct(request.field_name, request.context_text)
    return schemas.ReconstructionOutput(
        document_id=request.document_id,
        field_name=request.field_name,
        suggested_value=result.get("suggested_value", ""),
        basis="ai_reconstruction",
        confidence=result.get("confidence", "low")
    )

@app.post("/synthesize", response_model=schemas.SynthesisOutput)
def synthesize_documents(request: schemas.SynthesizeRequest) -> schemas.SynthesisOutput:
    result = llm_synthesize(request.documents)
    return schemas.SynthesisOutput(
        case_id=request.case_id,
        documents_included=request.documents,
        narrative=result.get("narrative", "")
    )

@app.get("/case/{id}")
def get_case(id: str) -> Dict[str, Any]:
    # Aggregates components with graceful degradation
    conn = get_db()
    
    def safe_get(table, id_field, id_val):
        try:
            row = conn.execute(f"SELECT * FROM {table} WHERE {id_field} = ?", (id_val,)).fetchone()
            return dict(row) if row else {}
        except Exception as e:
            print(f"DB Error getting {table}: {e}")
            return {}

    case_data = safe_get("cases", "id", id)
    evidence_data = safe_get("evidence", "case_id", id)
    followup_data = safe_get("followup_drafts", "case_id", id)
    synthesis_data = safe_get("synthesis_narratives", "case_id", id)
    
    # Graceful degradation logic: return what we have, even if parts are missing
    conn.close()
    
    return {
        "case_id": id,
        "details": case_data,
        "evidence": evidence_data,
        "followup": followup_data,
        "synthesis": synthesis_data
    }
