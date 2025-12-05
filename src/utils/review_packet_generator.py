import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import AgentContext
from src.config.settings import settings
from src.utils.output_manager import save_review_packet


logger = logging.getLogger(__name__)


@dataclass
class KPIEvaluationResult:
    """Result container for KPI evaluation."""

    passed: bool
    failed_kpis: List[Dict[str, Any]] = field(default_factory=list)
    severity: str = "warning"  # warning | critical
    summary: str = ""


class ReviewPacketGenerator:
    """Generate review packets when quality KPIs fail."""

    COMPOSITE_THRESHOLD = 0.60
    CRITICAL_COMPOSITE = 0.50
    DUPLICATE_THRESHOLD = 0.15
    DUPLICATE_CRITICAL = 0.30
    METRIC_MIN = 5
    TOPIC_COVERAGE_TOLERANCE = 1.0  # percentage points

    @classmethod
    def evaluate_kpis(
        cls,
        critic_scores: Optional[Dict[str, Any]],
        formatter_metrics: Optional[Dict[str, Any]],
        context: AgentContext,
    ) -> KPIEvaluationResult:
        critic_scores = critic_scores or {}
        formatter_metrics = formatter_metrics or {}
        metrics_data = cls._extract_metrics_map(formatter_metrics)
        analytics_expected_fields = metrics_data.get("analytics_expected_fields") or []
        analytics_checks_enabled = bool(
            settings.enable_metrics_monitoring
            and metrics_data.get("analytics_checks_enabled")
            and analytics_expected_fields
        )

        failed: List[Dict[str, Any]] = []
        severity = "warning"

        # Composite quality score
        composite = cls._safe_float(critic_scores.get("composite_score"))
        if composite is not None and composite < cls.COMPOSITE_THRESHOLD:
            sev = "critical" if composite < cls.CRITICAL_COMPOSITE else "warning"
            severity = cls._max_severity(severity, sev)
            failed.append(
                {
                    "kpi": "Composite Score",
                    "threshold": f">= {cls.COMPOSITE_THRESHOLD:.2f}",
                    "actual": f"{composite:.2f}",
                    "severity": sev,
                    "details": critic_scores.get("issues_found") or [],
                }
            )

        # Duplicate ratio
        duplicate_ratio = cls._safe_float(
            critic_scores.get("duplicate_ratio")
            or critic_scores.get("insight_duplicate_ratio")
        )
        if duplicate_ratio is not None and duplicate_ratio > cls.DUPLICATE_THRESHOLD:
            sev = "critical" if duplicate_ratio >= cls.DUPLICATE_CRITICAL else "warning"
            severity = cls._max_severity(severity, sev)
            failed.append(
                {
                    "kpi": "Duplicate Ratio",
                    "threshold": f"< {cls.DUPLICATE_THRESHOLD:.2f}",
                    "actual": f"{duplicate_ratio:.2f}",
                    "severity": sev,
                    "details": critic_scores.get("duplicate_examples") or [],
                }
            )

        # Metric references density
        metric_refs = cls._safe_int(
            critic_scores.get("metric_references_count")
            or critic_scores.get("metric_density_count")
        )
        if metric_refs is not None and metric_refs < cls.METRIC_MIN:
            failed.append(
                {
                    "kpi": "Metric References",
                    "threshold": f">= {cls.METRIC_MIN}",
                    "actual": str(metric_refs),
                    "severity": "warning",
                    "details": critic_scores.get("rewrite_guidance") or [],
                }
            )

        # Topic coverage totals
        topic_percentage_total = cls._safe_float(
            metrics_data.get("topic_percentage_total")
            or metrics_data.get("topic_percentages_total")
        )
        if topic_percentage_total is not None:
            if abs(topic_percentage_total - 100.0) > cls.TOPIC_COVERAGE_TOLERANCE:
                failed.append(
                    {
                        "kpi": "Topic Coverage",
                        "threshold": "100% ±1%",
                        "actual": f"{topic_percentage_total:.2f}%",
                        "severity": "warning",
                        "details": "Topic percentages should sum to ~100%.",
                    }
                )

        # Topic fallback usage
        topic_fallback = cls._safe_int(
            metrics_data.get("topic_fallback_used")
            or metrics_data.get("topic_fallback_count")
        )
        if topic_fallback is not None and topic_fallback > 0:
            failed.append(
                {
                    "kpi": "Topic Fallback Usage",
                    "threshold": "0 fallbacks",
                    "actual": str(topic_fallback),
                    "severity": "warning",
                    "details": "Fallback topics reduce specificity.",
                }
            )

        # Analytics coverage (CSAT/Fin/Churn)
        analytics_missing = []
        if analytics_checks_enabled:
            expected_set = {str(field).lower() for field in analytics_expected_fields}
            if "csat" in expected_set:
                csat_coverage = cls._safe_float(
                    metrics_data.get("csat_coverage_pct")
                    or metrics_data.get("csat_coverage")
                )
                if csat_coverage is None:
                    analytics_missing.append("CSAT coverage")
            if "fin" in expected_set:
                fin_deflection = cls._safe_float(metrics_data.get("fin_deflection_rate"))
                if fin_deflection is None:
                    analytics_missing.append("Fin deflection rate")
            if "churn" in expected_set:
                churn_signals = cls._safe_int(metrics_data.get("churn_risk_count"))
                if churn_signals is None:
                    analytics_missing.append("Churn-risk counts")
            if analytics_missing:
                failed.append(
                    {
                        "kpi": "Analytics Coverage",
                        "threshold": "CSAT + Fin deflection + Churn coverage present",
                        "actual": "Missing: " + ", ".join(analytics_missing),
                        "severity": "warning",
                        "details": analytics_missing,
                    }
                )

        if settings.force_review_packet_failure:
            failed.append(
                {
                    "kpi": "Forced Failure",
                    "threshold": "Validation override enabled",
                    "actual": "FORCE_REVIEW_PACKET_FAILURE=1",
                    "severity": "warning",
                    "details": ["Forced failure for validation script"],
                }
            )

        passed = len(failed) == 0
        summary = "KPIs met" if passed else f"{len(failed)} KPI(s) failed"
        return KPIEvaluationResult(
            passed=passed,
            failed_kpis=failed,
            severity=severity,
            summary=summary,
        )

    @classmethod
    def generate_review_packet(
        cls,
        evaluation_result: KPIEvaluationResult,
        context: AgentContext,
        output_dir: Path,
    ) -> Optional[Path]:
        """Generate markdown review packet and persist to disk."""
        analysis_id = getattr(context, "analysis_id", None) or context.metadata.get(
            "analysis_id", "unknown"
        )
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        exec_summary_lines = []
        for failure in evaluation_result.failed_kpis:
            severity = failure.get("severity", "warning").title()
            exec_summary_lines.append(f"- [{severity}] {failure.get('kpi')}")
        executive_summary = "\n".join(exec_summary_lines) or "Quality gates failed."

        kpi_rows = [
            "| KPI | Threshold | Actual | Severity |",
            "|-----|-----------|--------|----------|",
        ]
        for failure in evaluation_result.failed_kpis:
            kpi_rows.append(
                f"| {failure.get('kpi')} | {failure.get('threshold')} | "
                f"{failure.get('actual')} | {failure.get('severity', 'warning').title()} |"
            )

        artifacts = cls._build_artifacts(output_dir)
        artifacts_lines = [
            f"- [Execution Log]({artifacts.get('execution_log')})"
            if artifacts.get("execution_log")
            else "- Execution Log not found",
            f"- [Full JSON Output]({artifacts.get('json_output')})"
            if artifacts.get("json_output")
            else "- JSON output not found",
            f"- [Critic Scores]({artifacts.get('critic_scores')})"
            if artifacts.get("critic_scores")
            else "- Critic scores not found",
        ]

        markdown = "\n".join(
            [
                "# Quality Review Packet",
                "",
                f"**Analysis ID**: {analysis_id}",
                f"**Generated**: {timestamp}",
                f"**Status**: ⚠️ REVIEW REQUIRED",
                "",
                "## Executive Summary",
                executive_summary,
                "",
                "## Failed KPIs",
                *kpi_rows,
                "",
                "## Detailed Findings",
            ]
        )

        for failure in evaluation_result.failed_kpis:
            details = failure.get("details") or []
            if isinstance(details, str):
                details = [details]
            markdown += "\n".join(
                [
                    f"### {failure.get('kpi')} ({failure.get('severity', 'warning').title()})",
                    f"- **Issue**: {failure.get('threshold')} not met",
                    f"- **Actual**: {failure.get('actual')}",
                ]
            )
            if details:
                markdown += "\n- " + "\n- ".join(str(d) for d in details)
            markdown += "\n\n"

        markdown += "\n".join(
            [
                "## Artifacts",
                *artifacts_lines,
                "",
                "## Recommended Actions",
                "1. Review insights for specificity and metric density.",
                "2. Address duplicate narratives before publishing.",
                "3. Investigate missing analytics coverage (CSAT/Fin/Churn).",
            ]
        )

        try:
            packet_path = save_review_packet(
                packet_content=markdown, output_dir=output_dir, analysis_id=str(analysis_id)
            )
            if packet_path:
                logger.info("Review packet saved to %s", packet_path)
            return packet_path
        except Exception as exc:
            logger.error("Failed to save review packet: %s", exc)
            return None

    @staticmethod
    def _build_artifacts(output_dir: Path) -> Dict[str, str]:
        """Locate common artifacts for linking inside the packet."""
        artifacts = {
            "execution_log": "",
            "json_output": "",
            "critic_scores": "",
        }
        if not output_dir or not output_dir.exists():
            return artifacts

        for path in output_dir.iterdir():
            name = path.name
            if "execution" in name and name.endswith(".log"):
                artifacts["execution_log"] = str(path)
            if "voice-of-customer" in name and name.endswith(".json"):
                artifacts["json_output"] = str(path)
            if "critic" in name and name.endswith(".json"):
                artifacts["critic_scores"] = str(path)
        return artifacts

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _max_severity(current: str, candidate: str) -> str:
        order = {"warning": 0, "critical": 1}
        return candidate if order.get(candidate, 0) > order.get(current, 0) else current

    @staticmethod
    def _extract_metrics_map(formatter_metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(formatter_metrics, dict):
            return {}
        nested = formatter_metrics.get("metrics")
        if isinstance(nested, dict):
            return nested
        return formatter_metrics

