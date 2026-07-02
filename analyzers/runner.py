"""Run analyzers over playbook shared_data observables."""

from __future__ import annotations

from typing import Optional

from analyzers.base import VERDICTS, AnalyzerReport
from analyzers.registry import AnalyzerRegistry


def run_analyzers(
    shared_data: Optional[dict],
    analyzer_ids: Optional[list[str]] = None,
    obs_types: Optional[list[str]] = None,
) -> list[AnalyzerReport]:
    """Enrich every observable in shared_data and record verdict summaries.

    Writes per-analyzer reports into each observable's `enrichment` and sets
    rollup keys `analysis_max_score` / `analysis_verdict` on shared_data so
    playbook conditions can branch on the outcome.
    """
    from core.observables import wrap_shared_data

    registry = AnalyzerRegistry.get_instance()
    ctx = wrap_shared_data(shared_data)
    data = ctx.raw

    reports: list[AnalyzerReport] = []
    for observable in ctx.observables():
        if obs_types and observable.type not in obs_types:
            continue
        if analyzer_ids:
            analyzers = [registry.get(aid) for aid in analyzer_ids]
            analyzers = [a for a in analyzers if a and a.supports(observable.type)]
        else:
            analyzers = registry.for_type(observable.type)
        for analyzer in analyzers:
            if not analyzer.available:
                continue
            report = analyzer.analyze(observable.type, observable.value)
            reports.append(report)
            if not report.error:
                ctx.merge_enrichment(
                    observable.type,
                    observable.value,
                    report.analyzer,
                    {
                        'verdict': report.verdict,
                        'score': report.score,
                        'summary': report.summary,
                        'cached': report.cached,
                    },
                )

    scored = [r for r in reports if not r.error]
    if scored:
        data['analysis_max_score'] = max(r.score for r in scored)
        worst = max(scored, key=lambda r: VERDICTS.index(r.verdict))
        data['analysis_verdict'] = worst.verdict
    return reports
