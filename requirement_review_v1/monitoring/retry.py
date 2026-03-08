"""Retry metadata helpers for non-blocking workflow steps."""

from __future__ import annotations

from typing import Any


def build_retry_metadata(
    *,
    retryable: bool,
    attempt: int = 1,
    max_attempts: int = 3,
    strategy: str = "manual",
    backoff_seconds: int = 0,
    last_error: str = "",
    state: str = "",
) -> dict[str, Any]:
    normalized_attempt = max(1, int(attempt or 1))
    normalized_max_attempts = max(normalized_attempt, int(max_attempts or normalized_attempt))
    normalized_last_error = str(last_error or "").strip()

    if state:
        resolved_state = str(state).strip()
    elif not retryable:
        resolved_state = "not_needed"
    elif normalized_attempt >= normalized_max_attempts:
        resolved_state = "exhausted"
    else:
        resolved_state = "available"

    if resolved_state == "available":
        recommended_action = "manual_retry"
    elif resolved_state == "blocked":
        recommended_action = "retry_after_dependency_recovery"
    elif resolved_state == "exhausted":
        recommended_action = "escalate"
    else:
        recommended_action = "none"

    return {
        "retryable": bool(retryable),
        "state": resolved_state,
        "attempt": normalized_attempt,
        "max_attempts": normalized_max_attempts,
        "strategy": str(strategy or "manual").strip() or "manual",
        "backoff_seconds": max(0, int(backoff_seconds or 0)),
        "last_error": normalized_last_error,
        "recommended_action": recommended_action,
    }


def retry_metadata_for_status(
    *,
    status: str,
    non_blocking: bool,
    error_message: str = "",
    attempt: int = 1,
    max_attempts: int = 3,
    strategy: str = "manual",
) -> dict[str, Any]:
    normalized_status = str(status or "unknown").strip().lower()
    normalized_error = str(error_message or "").strip()
    success_statuses = {"ok", "success", "completed"}

    if normalized_status in success_statuses:
        return build_retry_metadata(
            retryable=False,
            attempt=attempt,
            max_attempts=max_attempts,
            strategy=strategy,
        )

    if normalized_status == "skipped":
        return build_retry_metadata(
            retryable=bool(non_blocking and normalized_error),
            attempt=attempt,
            max_attempts=max_attempts,
            strategy=strategy,
            last_error=normalized_error,
            state="blocked" if non_blocking and normalized_error else "not_needed",
        )

    return build_retry_metadata(
        retryable=bool(non_blocking),
        attempt=attempt,
        max_attempts=max_attempts,
        strategy=strategy,
        last_error=normalized_error,
    )
