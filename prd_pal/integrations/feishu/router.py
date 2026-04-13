from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .models import (
    FeishuChallengeEvent,
    FeishuClarificationRequest,
    FeishuEventEnvelope,
    FeishuSubmitRequest,
)
from .security import FeishuSignatureVerificationError, verify_feishu_signature


SubmitReviewRun = Callable[..., Awaitable[dict[str, str]]]
SubmitClarification = Callable[..., dict[str, Any]]


def _invalid_signature_response(exc: FeishuSignatureVerificationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


def create_feishu_router(
    *,
    submit_review_run: SubmitReviewRun,
    submit_clarification: SubmitClarification,
) -> APIRouter:
    router = APIRouter(prefix="/api/feishu", tags=["feishu"])

    @router.post("/events")
    async def handle_feishu_events(request: Request) -> JSONResponse:
        body = await request.body()
        try:
            verify_feishu_signature(headers=request.headers, body=body)
        except FeishuSignatureVerificationError as exc:
            return _invalid_signature_response(exc)

        payload = json.loads(body.decode("utf-8") or "{}")
        envelope = FeishuEventEnvelope.model_validate(payload)
        if envelope.is_challenge():
            challenge = FeishuChallengeEvent.model_validate(payload)
            return JSONResponse(status_code=200, content={"challenge": challenge.challenge})

        return JSONResponse(status_code=200, content={"code": 0, "message": "ok"})

    @router.post("/submit", response_model=None)
    async def submit_feishu_review(payload: FeishuSubmitRequest, request: Request) -> Any:
        body = await request.body()
        try:
            verify_feishu_signature(headers=request.headers, body=body)
        except FeishuSignatureVerificationError as exc:
            return _invalid_signature_response(exc)

        review_payload = payload.to_review_payload()
        return await submit_review_run(
            **review_payload,
            audit_context=payload.build_audit_context(),
        )

    @router.post("/clarification", response_model=None)
    async def submit_feishu_clarification(payload: FeishuClarificationRequest, request: Request) -> Any:
        body = await request.body()
        try:
            verify_feishu_signature(headers=request.headers, body=body)
        except FeishuSignatureVerificationError as exc:
            return _invalid_signature_response(exc)

        run_id = str(payload.run_id or "").strip()
        try:
            result_payload = submit_clarification(
                run_id=run_id,
                answers=payload.to_answers_payload(),
                audit_context=payload.build_audit_context(),
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail={"code": "run_not_found", "message": str(exc)},
            ) from exc
        except PermissionError as exc:
            message = str(exc)
            code = "feishu_context_required" if "requires" in message else "run_access_denied"
            raise HTTPException(
                status_code=403,
                detail={"code": code, "message": message},
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "clarification_unavailable", "message": str(exc), "run_id": run_id},
            ) from exc
        except TypeError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "invalid_clarification_payload", "message": str(exc), "run_id": run_id},
            ) from exc

        clarification = result_payload.get("clarification", {}) if isinstance(result_payload, dict) else {}
        has_pending_questions = bool(
            isinstance(clarification, dict)
            and clarification.get("triggered")
            and clarification.get("status") == "pending"
        )
        return {
            "run_id": run_id,
            "clarification_status": str(clarification.get("status", "") or "not_needed"),
            "has_pending_questions": has_pending_questions,
            "clarification": clarification,
            "result_page": {
                "path": f"/run/{run_id}",
                "url": f"/run/{run_id}",
            },
        }

    return router
