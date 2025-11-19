"""Human-readable formatter for distribution audit results (US6a)."""

from __future__ import annotations

from typing import List

from quant_scenario_engine.distributions.distribution_audit import DistributionAuditResult, ModelScore


def _format_scores(scores: List[ModelScore]) -> str:
    lines = ["Scores (higher is better):"]
    ranked = sorted(scores, key=lambda s: s.total_score, reverse=True)
    for idx, score in enumerate(ranked, start=1):
        parts = ", ".join(f"{k}={v:.3f}" for k, v in score.components.items())
        lines.append(f"  {idx}. {score.model_name} -> {score.total_score:.3f} ({parts})")
    return "\n".join(lines)


def format_audit_result(result: DistributionAuditResult) -> str:
    """Return a concise textual summary for CLI printing."""
    header = f"Distribution Audit for {result.symbol}"
    best_name = result.best_model.name if result.best_model else "Unavailable"
    best_score = next((s.total_score for s in result.scores if s.model_name == best_name), None)
    tail_notes = []
    for tm in result.tail_metrics:
        tail_notes.append(f"  {tm.model_name}: tail_error_99={tm.tail_error_99:.3f}")

    score_display = f"{best_score:.3f}" if best_score is not None else "n/a"

    sections = [
        header,
        "=" * len(header),
        f"Best Model: {best_name} (score={score_display})",
        _format_scores(result.scores),
    ]

    if tail_notes:
        sections.append("Tail Diagnostics (99% relative error):")
        sections.extend(tail_notes)

    failures = [fr for fr in result.fit_results if not fr.fit_success]
    if failures:
        sections.append("Warnings:")
        for fr in failures:
            message = fr.fit_message or fr.error or "fit failed"
            sections.append(f"  {fr.model_name}: {message}")

    return "\n".join(sections)


__all__ = ["format_audit_result"]
