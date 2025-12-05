#!/usr/bin/env python3
"""
Validation harness for the LangChain tool wrappers added in Phase 2.

The script exercises TopicDetectionTool, InsightTool, EditorTool, and
OutputFormatterTool against a small slice of sample data so we can verify
schema round-trips without running the full VoC pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.agents.tools import (  # noqa: E402
    EditorTool,
    InsightTool,
    OutputFormatterTool,
    TopicDetectionTool,
)


logger = logging.getLogger("tool_wrappers")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DEFAULT_DATA_DIR = PROJECT_ROOT / "reference_data" / "voice-of-customer_Last-Week_dec-1-6-41pm"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exercise LangChain tool wrappers with sample data")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing reference artifacts (default: %(default)s)",
    )
    parser.add_argument(
        "--conversation-count",
        type=int,
        default=10,
        help="Number of sample conversations to feed into the tools",
    )
    parser.add_argument(
        "--analysis-id",
        type=str,
        default=f"tool-wrapper-{int(time.time())}",
        help="Analysis ID to stamp on AgentContext objects",
    )
    return parser.parse_args()


def load_audit_metadata(data_dir: Path) -> Tuple[datetime, datetime]:
    """Extract start/end dates from the audit trail JSON if available."""
    audit_files = sorted(data_dir.glob("audit_trail_*.json"))
    if not audit_files:
        logger.warning("No audit trail JSON found under %s", data_dir)
        now = datetime.now(timezone.utc)
        return now - timedelta(days=7), now

    try:
        payload = json.loads(audit_files[0].read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to parse %s: %s", audit_files[0], exc)
        now = datetime.now(timezone.utc)
        return now - timedelta(days=7), now

    steps = payload.get("steps", [])
    for step in steps:
        details = step.get("details") or {}
        if "start_date" in details and "end_date" in details:
            return (
                datetime.fromisoformat(str(details["start_date"]) + "T00:00:00+00:00"),
                datetime.fromisoformat(str(details["end_date"]) + "T23:59:59+00:00"),
            )

    now = datetime.now(timezone.utc)
    return now - timedelta(days=7), now


def load_sample_conversations(data_dir: Path, count: int) -> List[Dict[str, Any]]:
    """
    Load a small subset of conversations.

    The reference folder does not store raw conversations, so we fall back to generating
    synthetic payloads that match the shape TopicDetectionAgent expects.
    """
    sample_files = sorted(data_dir.glob("conversations*.json"))
    if sample_files:
        try:
            data = json.loads(sample_files[0].read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[:count]
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to parse %s: %s", sample_files[0], exc)

    logger.warning(
        "Conversation snapshot not found under %s; generating %d synthetic examples",
        data_dir,
        count,
    )
    return _generate_mock_conversations(count)


def _generate_mock_conversations(count: int) -> List[Dict[str, Any]]:
    topics = [
        ("Billing", "My invoice is wrong and needs a refund."),
        ("Bug", "The workspace keeps crashing when I click export."),
        ("Account", "I cannot reset my password after enabling SSO."),
        ("Product Question", "How do I enable Fin to auto-resolve tickets?"),
        ("Feedback", "Please add a live roadmap widget."),
    ]
    conversations: List[Dict[str, Any]] = []
    for idx in range(count):
        topic, text = random.choice(topics)
        conv_id = f"conv_{idx:04d}"
        conversations.append(
            {
                "id": conv_id,
                "created_at": int(time.time()) - idx * 3600,
                "custom_attributes": {"topic_hint": topic},
                "source": {
                    "author": {"type": "user", "id": f"user_{idx:04d}"},
                    "body": text,
                },
                "conversation_parts": {"conversation_parts": []},
                "tags": {"tags": [{"name": topic}]},
            }
        )
    return conversations


def build_topic_sentiments(topic_detection: Dict[str, Any]) -> Dict[str, Any]:
    """Create lightweight TopicSentimentAgent-style payloads so InsightAgent can run."""
    sentiments: Dict[str, Any] = {}
    for topic in topic_detection.get("topic_distribution", {}):
        sentiments[topic] = {
            "data": {
                "sentiment_insight": f"Customers discussing {topic} skew neutral in this sample.",
                "sentiment": "neutral",
            }
        }
    return sentiments


async def main() -> None:
    args = parse_args()
    data_dir: Path = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    start_date, end_date = load_audit_metadata(data_dir)
    conversations = load_sample_conversations(data_dir, args.conversation_count)

    logger.info(
        "Loaded %d conversations from %s (analysis window %s → %s)",
        len(conversations),
        data_dir,
        start_date.date(),
        end_date.date(),
    )

    topic_tool = TopicDetectionTool()
    insight_tool = InsightTool()
    editor_tool = EditorTool()
    formatter_tool = OutputFormatterTool()

    # ------------------------------------------------------------------ Topic Detection
    topic_result = await topic_tool.safe_execute(
        conversations=conversations,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        analysis_id=args.analysis_id,
        metadata={"source": "tool_wrapper_harness"},
    )
    if not topic_result.success:
        raise RuntimeError(f"TopicDetectionTool failed: {topic_result.error_message}")
    logger.info("✅ TopicDetectionTool passed")

    topic_output: Dict[str, Any] = topic_result.data or {}
    topic_sentiments = build_topic_sentiments(topic_output)
    previous_results: Dict[str, Any] = {
        "TopicDetectionAgent": {"success": True, "data": topic_output},
        "TopicSentimentAgent": topic_sentiments,
        "TopicSentiments": topic_sentiments,
    }

    # ------------------------------------------------------------------ Insight Synthesis
    insight_result = await insight_tool.safe_execute(
        previous_results=previous_results,
        analysis_id=args.analysis_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        conversations=conversations,
        metadata={"source": "tool_wrapper_harness"},
    )
    if not insight_result.success:
        raise RuntimeError(f"InsightTool failed: {insight_result.error_message}")
    logger.info("✅ InsightTool passed")

    insight_output: Dict[str, Any] = insight_result.data or {}
    previous_results["InsightAgent"] = {"success": True, "data": insight_output}

    # ------------------------------------------------------------------ Editor / Critic
    editor_result = await editor_tool.safe_execute(
        previous_results=previous_results,
        analysis_id=args.analysis_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        conversations=conversations,
        metadata={"source": "tool_wrapper_harness"},
    )
    if not editor_result.success:
        raise RuntimeError(f"EditorTool failed: {editor_result.error_message}")
    logger.info("✅ EditorTool passed")

    editor_output: Dict[str, Any] = editor_result.data or {}
    previous_results["EditorAgent"] = {"success": True, "data": editor_output}

    # Provide placeholders for other agents the formatter references.
    previous_results.setdefault("SegmentationAgent", {"data": {}})
    previous_results.setdefault("FinPerformanceAgent", {"data": {}})
    previous_results.setdefault("BpoPerformanceAgent", {"data": {}})
    previous_results.setdefault("TrendAgent", {"data": {}})
    previous_results.setdefault("SubTopicDetectionAgent", {"data": {}})
    previous_results.setdefault("TopicExamples", {})
    previous_results.setdefault("AnalyticalInsights", {})

    # ------------------------------------------------------------------ Output Formatter
    formatter_result = await formatter_tool.safe_execute(
        previous_results=previous_results,
        conversations=conversations,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        analysis_id=args.analysis_id,
        metadata={"source": "tool_wrapper_harness"},
    )
    if not formatter_result.success:
        raise RuntimeError(f"OutputFormatterTool failed: {formatter_result.error_message}")
    logger.info("✅ OutputFormatterTool passed")

    formatted_data: Dict[str, Any] = formatter_result.data or {}
    logger.info(
        "📄 Formatter produced %d topic cards and %d characters of markdown",
        formatted_data.get("total_topics"),
        len(formatted_data.get("formatted_output", "")),
    )


if __name__ == "__main__":
    asyncio.run(main())

