"""Helpers for constructing structured task packs."""

from .schemas import ExecutionPack, ImplementationPack, RiskSummaryItem, TestPack


def build_implementation_pack(**data: object) -> ImplementationPack:
    """Validate and create an implementation pack."""

    return ImplementationPack.model_validate(data)


def build_test_pack(**data: object) -> TestPack:
    """Validate and create a test pack."""

    return TestPack.model_validate(data)


def build_execution_pack(
    implementation_pack: ImplementationPack | dict[str, object],
    test_pack: TestPack | dict[str, object],
    risk_pack: list[RiskSummaryItem | dict[str, object]] | None = None,
    handoff_strategy: str = "sequential",
    pack_type: str = "execution_pack",
    pack_version: str = "1.0",
) -> ExecutionPack:
    """Validate and create a full execution pack."""

    risk_items = risk_pack or []
    return ExecutionPack.model_validate(
        {
            "pack_type": pack_type,
            "pack_version": pack_version,
            "implementation_pack": implementation_pack,
            "test_pack": test_pack,
            "risk_pack": risk_items,
            "handoff_strategy": handoff_strategy,
        }
    )
