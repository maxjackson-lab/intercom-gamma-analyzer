"""Historical snapshot service for VoC analysis.
Provides high-level operations around DuckDBStorage for saving and retrieving
analysis snapshots, performing week-over-week comparisons and migrating legacy
JSON data from the previous storage approach.

NOTE: This is a first cut inspired by the November-4 plan.  Many helper
functions are intentionally lightweight – they can be expanded later as
additional agents supply richer data.  All critical write paths are wrapped in
try/except so snapshot failure never blocks the main analysis pipeline.
"""
from __future__ import annotations

from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import json
import logging
import re

from pydantic import BaseModel, Field, ConfigDict, field_validator, TypeAdapter, ValidationError

from src.services.duckdb_storage import DuckDBStorage
from src.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic Models for Validation
# ---------------------------------------------------------------------------

class SnapshotData(BaseModel):
    """Validated snapshot data model for type safety and schema enforcement."""
    
    snapshot_id: str = Field(..., description="Unique snapshot identifier (e.g., weekly_20251107)")
    analysis_type: str = Field(..., pattern=r'^(weekly|monthly|quarterly|custom)$')
    period_start: date = Field(..., description="Start date of analysis period")
    period_end: date = Field(..., description="End date of analysis period")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total_conversations: int = Field(ge=0, default=0)
    date_range_label: str = Field(default="", max_length=200)
    insights_summary: str = Field(default="", max_length=500)
    
    # JSON fields with type adapters
    topic_volumes: Dict[str, int] = Field(default_factory=dict)
    topic_sentiments: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    tier_distribution: Dict[str, int] = Field(default_factory=dict)
    agent_attribution: Optional[Dict[str, int]] = None
    resolution_metrics: Optional[Dict[str, float]] = None
    fin_performance: Optional[Dict[str, Any]] = None
    key_patterns: Optional[List[str]] = None
    
    # Review metadata
    reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(
        extra='forbid',  # Catch typos and unexpected fields
        validate_assignment=True,  # Validate on attribute assignment
        str_strip_whitespace=True  # Auto-strip strings
    )
    
    @field_validator('snapshot_id')
    @classmethod
    def validate_snapshot_id_format(cls, v: str) -> str:
        """Ensure snapshot_id follows expected format."""
        if not re.match(r'^(weekly|monthly|quarterly|custom)_\d{8}$', v):
            raise ValueError(f"snapshot_id must match format 'type_YYYYMMDD', got: {v}")
        return v
    
    @field_validator('period_end')
    @classmethod
    def validate_period_order(cls, v: date, info) -> date:
        """Ensure period_end is after period_start."""
        if 'period_start' in info.data and v < info.data['period_start']:
            raise ValueError("period_end must be >= period_start")
        return v


class ComparisonData(BaseModel):
    """Validated comparison data for week-over-week analysis."""
    
    comparison_id: str = Field(..., pattern=r'^comp_')
    comparison_type: str = Field(default="week_over_week")
    current_snapshot_id: str
    prior_snapshot_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    volume_changes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    sentiment_changes: Optional[Dict[str, Dict[str, Any]]] = None
    resolution_changes: Optional[Dict[str, Any]] = None
    significant_changes: Optional[List[str]] = None
    emerging_patterns: Optional[List[str]] = None
    declining_patterns: Optional[List[str]] = None
    
    model_config = ConfigDict(extra='forbid')


# ---------------------------------------------------------------------------
# TypeAdapters for High-Performance JSON Serialization
# ---------------------------------------------------------------------------

# Module-level TypeAdapters for reuse (3-4x faster than json.dumps/loads)
TopicVolumesAdapter = TypeAdapter(Dict[str, int])
TopicSentimentsAdapter = TypeAdapter(Dict[str, Dict[str, float]])
TierDistributionAdapter = TypeAdapter(Dict[str, int])
AgentAttributionAdapter = TypeAdapter(Dict[str, int])
KeyPatternsAdapter = TypeAdapter(List[str])


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _first_sentences(text: str, max_chars: int = 200) -> str:
    """Return the first 2-3 sentences from *text* limited to *max_chars*."""
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?]) +", text.strip())
    summary = " ".join(sentences[:3]).strip()
    return summary[:max_chars]


def _pct_change(old: int | float, new: int | float) -> float:
    if old == 0:
        return 0.0
    return round((new - old) / old, 4)


# ---------------------------------------------------------------------------
# Main facade
# ---------------------------------------------------------------------------

class HistoricalSnapshotService:  # pylint: disable=too-many-public-methods
    """Facade around :class:`DuckDBStorage` for historical VoC snapshots."""

    def __init__(self, duckdb_storage: DuckDBStorage) -> None:
        self.db = duckdb_storage
        self.db.ensure_schema()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_snapshot(self, analysis_output: Dict[str, Any], analysis_type: str = "weekly") -> str:
        """Save *analysis_output* produced by TopicOrchestrator with Pydantic validation.

        Returns the generated ``snapshot_id`` regardless of save success so the
        caller can embed it in outgoing data.  Errors are swallowed with a log
        entry so analysis never crashes because of storage.
        
        Uses Pydantic validation for type safety and better error messages.
        """
        try:
            week_id = analysis_output.get("week_id")  # e.g. "2025_W45"
            period_label = analysis_output.get("period_label", "")
            # For now we treat week_id date parsing very simply – YYYYMMDD at end
            period_start = analysis_output.get("period_start")
            period_end = analysis_output.get("period_end")
            if not period_start or not period_end:
                # Fallback to week_id ISO week parsing.
                if week_id and re.match(r"^\d{4}_W\d{2}$", week_id):
                    year, week = week_id.split("_W")
                    # Monday of ISO week
                    d = datetime.strptime(f"{year}-{week}-1", "%Y-%W-%w").date()
                    period_start = d
                    period_end = d + timedelta(days=6)
            snapshot_id = self._generate_snapshot_id(period_start or date.today(), analysis_type)

            agent_results: Dict[str, Any] = analysis_output.get("agent_results", {})

            # Build raw data dict
            raw_data: Dict[str, Any] = {
                "snapshot_id": snapshot_id,
                "analysis_type": analysis_type,
                "period_start": period_start,
                "period_end": period_end,
                "created_at": datetime.utcnow(),
                "total_conversations": analysis_output.get("summary", {}).get("total_conversations", 0),
                "date_range_label": period_label,
                "insights_summary": _first_sentences(analysis_output.get("formatted_report", "")),
                "topic_volumes": self._extract_topic_volumes(agent_results),
                "topic_sentiments": self._extract_topic_sentiments(agent_results),
                "tier_distribution": self._extract_tier_distribution(agent_results),
                "agent_attribution": analysis_output.get("metrics", {}).get("agent_attribution"),
                "resolution_metrics": analysis_output.get("metrics", {}).get("resolution_metrics"),
                "fin_performance": analysis_output.get("metrics", {}).get("fin_performance"),
                "key_patterns": analysis_output.get("metrics", {}).get("key_patterns"),
            }
            
            # Validate with Pydantic for type safety
            try:
                validated_snapshot = SnapshotData.model_validate(raw_data)
                logger.debug("Snapshot validation passed for %s", snapshot_id)
            except ValidationError as ve:
                logger.warning("Snapshot validation failed for %s: %s", snapshot_id, ve)
                # Continue with raw data if validation fails (backward compatibility)
                validated_snapshot = None
            
            # Store validated or raw data
            snapshot_dict = validated_snapshot.model_dump() if validated_snapshot else raw_data
            ok = self.db.store_analysis_snapshot(snapshot_dict)
            
            if ok:
                logger.info("Snapshot %s stored successfully", snapshot_id)
            else:
                logger.warning("Snapshot %s failed to store", snapshot_id)
            return snapshot_id
        except Exception as exc:  # noqa: broad-except
            logger.exception("save_snapshot – unexpected error: %s", exc)
            # Even if we failed we still want a deterministic id for caller.
            return self._generate_snapshot_id(date.today(), analysis_type)

    # ------------------------------------------------------------------
    def get_prior_snapshot(self, current_snapshot_id: str, analysis_type: str = "weekly") -> Optional[Dict[str, Any]]:
        current_date = self._parse_snapshot_date(current_snapshot_id)
        if not current_date:
            return None
        delta = {"weekly": 7, "monthly": 30, "quarterly": 90}.get(analysis_type, 7)
        prior_date = current_date - timedelta(days=delta)
        prior_id = self._generate_snapshot_id(prior_date, analysis_type)
        return self.db.get_analysis_snapshot(prior_id)

    # ------------------------------------------------------------------
    def calculate_comparison(self, current_snapshot: Dict[str, Any], prior_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive week-over-week comparison between snapshots.
        
        Returns dict with:
        - volume_changes: Topic volume deltas
        - sentiment_changes: Sentiment score changes per topic
        - resolution_changes: Resolution metric deltas
        - significant_changes: Filtered changes (>25% and >5 absolute)
        - emerging_patterns: New topics appearing
        - declining_patterns: Topics disappearing
        """
        try:
            comparison_id = f"comp_{current_snapshot['snapshot_id']}_{prior_snapshot['snapshot_id']}"
            
            # Calculate all comparison dimensions
            volume_changes = self._calculate_volume_deltas(current_snapshot, prior_snapshot)
            sentiment_changes = self._calculate_sentiment_deltas(current_snapshot, prior_snapshot)
            resolution_changes = self._calculate_resolution_deltas(current_snapshot, prior_snapshot)
            significant_changes = self._identify_significant_changes(volume_changes)
            emerging_patterns = self._detect_emerging_patterns(current_snapshot, prior_snapshot)
            declining_patterns = self._detect_declining_patterns(current_snapshot, prior_snapshot)
            
            comparison_data = {
                "comparison_id": comparison_id,
                "comparison_type": "week_over_week" if current_snapshot["analysis_type"] == "weekly" else "period",
                "current_snapshot_id": current_snapshot["snapshot_id"],
                "prior_snapshot_id": prior_snapshot["snapshot_id"],
                "volume_changes": volume_changes,
                "sentiment_changes": sentiment_changes,
                "resolution_changes": resolution_changes,
                "significant_changes": significant_changes,
                "emerging_patterns": emerging_patterns,
                "declining_patterns": declining_patterns,
            }
            
            # Store in DuckDB for historical retrieval
            self.db.store_comparative_analysis(comparison_data)
            logger.info(f"Comparison calculated: {len(significant_changes)} significant changes, "
                       f"{len(emerging_patterns)} emerging, {len(declining_patterns)} declining")
            
            return comparison_data
            
        except Exception as exc:
            logger.exception("calculate_comparison failed: %s", exc)
            # Return minimal valid structure on error
            return {
                "comparison_id": f"comp_error_{datetime.utcnow().isoformat()}",
                "comparison_type": "week_over_week",
                "current_snapshot_id": current_snapshot.get("snapshot_id", "unknown"),
                "prior_snapshot_id": prior_snapshot.get("snapshot_id", "unknown"),
                "volume_changes": {},
                "sentiment_changes": {},
                "resolution_changes": {},
                "significant_changes": [],
                "emerging_patterns": [],
                "declining_patterns": [],
            }

    # ------------------------------------------------------------------
    # Comparison helper methods
    # ------------------------------------------------------------------
    
    def _calculate_volume_deltas(self, current_snapshot: Dict[str, Any], prior_snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Calculate volume changes for all topics."""
        try:
            volume_changes: Dict[str, Dict[str, Any]] = {}
            cur_vol = current_snapshot.get("topic_volumes", {}) or {}
            prev_vol = prior_snapshot.get("topic_volumes", {}) or {}
            all_topics = set(cur_vol) | set(prev_vol)
            
            for topic in all_topics:
                cur = cur_vol.get(topic, 0)
                prev = prev_vol.get(topic, 0)
                volume_changes[topic] = {
                    "change": cur - prev,
                    "pct": _pct_change(prev, cur),
                    "current": cur,
                    "prior": prev,
                }
            
            return volume_changes
        except Exception as exc:
            logger.warning("_calculate_volume_deltas failed: %s", exc)
            return {}
    
    def _calculate_sentiment_deltas(self, current_snapshot: Dict[str, Any], prior_snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Calculate sentiment score changes per topic."""
        try:
            sentiment_changes: Dict[str, Dict[str, Any]] = {}
            cur_sent = current_snapshot.get("topic_sentiments", {}) or {}
            prev_sent = prior_snapshot.get("topic_sentiments", {}) or {}
            all_topics = set(cur_sent) | set(prev_sent)
            
            for topic in all_topics:
                cur_data = cur_sent.get(topic, {})
                prev_data = prev_sent.get(topic, {})
                
                # Skip if sentiment data missing for either period
                if not cur_data or not prev_data:
                    continue
                
                cur_positive = cur_data.get('positive', 0)
                cur_negative = cur_data.get('negative', 0)
                prev_positive = prev_data.get('positive', 0)
                prev_negative = prev_data.get('negative', 0)
                
                positive_delta = cur_positive - prev_positive
                negative_delta = cur_negative - prev_negative
                
                # Determine sentiment shift direction
                if abs(positive_delta) > 0.1:  # 10+ percentage point shift
                    if positive_delta > 0:
                        shift = "more positive"
                    else:
                        shift = "more negative"
                elif abs(negative_delta) > 0.1:
                    if negative_delta > 0:
                        shift = "more negative"
                    else:
                        shift = "more positive"
                else:
                    shift = "stable"
                
                sentiment_changes[topic] = {
                    'positive_delta': round(positive_delta, 3),
                    'negative_delta': round(negative_delta, 3),
                    'shift': shift
                }
            
            return sentiment_changes
        except Exception as exc:
            logger.warning("_calculate_sentiment_deltas failed: %s", exc)
            return {}
    
    def _calculate_resolution_deltas(self, current_snapshot: Dict[str, Any], prior_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate resolution metric deltas."""
        try:
            resolution_changes: Dict[str, Any] = {}
            cur_metrics = current_snapshot.get("resolution_metrics", {}) or {}
            prev_metrics = prior_snapshot.get("resolution_metrics", {}) or {}
            
            # Skip if no resolution data available
            if not cur_metrics or not prev_metrics:
                return {}
            
            # FCR rate delta (percentage point change)
            if 'fcr_rate' in cur_metrics and 'fcr_rate' in prev_metrics:
                fcr_delta = cur_metrics['fcr_rate'] - prev_metrics['fcr_rate']
                resolution_changes['fcr_rate_delta'] = round(fcr_delta, 3)
            
            # Resolution time delta (hours)
            if 'median_resolution_hours' in cur_metrics and 'median_resolution_hours' in prev_metrics:
                time_delta = cur_metrics['median_resolution_hours'] - prev_metrics['median_resolution_hours']
                resolution_changes['resolution_time_delta'] = round(time_delta, 2)
            
            # Reopen rate delta (if available)
            if 'reopen_rate' in cur_metrics and 'reopen_rate' in prev_metrics:
                reopen_delta = cur_metrics['reopen_rate'] - prev_metrics['reopen_rate']
                resolution_changes['reopen_rate_delta'] = round(reopen_delta, 3)
            
            # Overall interpretation
            improving_count = 0
            declining_count = 0
            
            if resolution_changes.get('fcr_rate_delta', 0) > 0:
                improving_count += 1
            elif resolution_changes.get('fcr_rate_delta', 0) < 0:
                declining_count += 1
                
            if resolution_changes.get('resolution_time_delta', 0) < 0:  # Lower time is better
                improving_count += 1
            elif resolution_changes.get('resolution_time_delta', 0) > 0:
                declining_count += 1
            
            if improving_count > declining_count:
                resolution_changes['interpretation'] = 'improving'
            elif declining_count > improving_count:
                resolution_changes['interpretation'] = 'declining'
            else:
                resolution_changes['interpretation'] = 'stable'
            
            return resolution_changes
        except Exception as exc:
            logger.warning("_calculate_resolution_deltas failed: %s", exc)
            return {}
    
    def _identify_significant_changes(self, volume_changes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify significant volume changes (>25% AND >5 conversations)."""
        try:
            significant = []
            
            for topic, changes in volume_changes.items():
                pct = changes.get('pct', 0)
                change = changes.get('change', 0)
                
                # Both conditions must be met
                if abs(pct) > 0.25 and abs(change) > 5:
                    direction = 'increasing' if change > 0 else 'decreasing'
                    alert = '⚠️' if change > 0 else '✓'
                    
                    significant.append({
                        'topic': topic,
                        'change': change,
                        'pct': pct,
                        'direction': direction,
                        'alert': alert,
                        'current': changes.get('current', 0),
                        'prior': changes.get('prior', 0)
                    })
            
            # Sort by absolute percentage change descending, limit to top 5
            significant.sort(key=lambda x: abs(x['pct']), reverse=True)
            return significant[:5]
            
        except Exception as exc:
            logger.warning("_identify_significant_changes failed: %s", exc)
            return []
    
    def _detect_emerging_patterns(self, current_snapshot: Dict[str, Any], prior_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect new topics appearing (emerging patterns)."""
        try:
            emerging = []
            cur_vol = current_snapshot.get("topic_volumes", {}) or {}
            prev_vol = prior_snapshot.get("topic_volumes", {}) or {}
            
            # Topics in current but not in prior
            new_topics = set(cur_vol.keys()) - set(prev_vol.keys())
            
            for topic in new_topics:
                volume = cur_vol[topic]
                
                # Filter out noise (topics with volume < 3)
                if volume >= 3:
                    emerging.append({
                        'topic': topic,
                        'volume': volume,
                        'context': 'New topic appeared this period'
                    })
            
            # Sort by volume descending
            emerging.sort(key=lambda x: x['volume'], reverse=True)
            return emerging
            
        except Exception as exc:
            logger.warning("_detect_emerging_patterns failed: %s", exc)
            return []
    
    def _detect_declining_patterns(self, current_snapshot: Dict[str, Any], prior_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect topics disappearing (declining patterns)."""
        try:
            declining = []
            cur_vol = current_snapshot.get("topic_volumes", {}) or {}
            prev_vol = prior_snapshot.get("topic_volumes", {}) or {}
            
            # Topics in prior but not in current
            disappeared_topics = set(prev_vol.keys()) - set(cur_vol.keys())
            
            for topic in disappeared_topics:
                prior_volume = prev_vol[topic]
                
                # Filter out noise (topics with prior volume < 3)
                if prior_volume >= 3:
                    declining.append({
                        'topic': topic,
                        'prior_volume': prior_volume,
                        'context': 'Topic disappeared this period'
                    })
            
            # Sort by prior volume descending
            declining.sort(key=lambda x: x['prior_volume'], reverse=True)
            return declining
            
        except Exception as exc:
            logger.warning("_detect_declining_patterns failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    def get_historical_context(self) -> Dict[str, Any]:
        snaps = self.db.get_snapshots_by_type("weekly", 1000)
        # Sort by period_start ascending to ensure stable baseline reference
        snaps = sorted(snaps, key=lambda s: s.get("period_start") or date.min)
        weeks_available = len(snaps)
        return {
            "has_baseline": weeks_available >= 4,
            "weeks_available": weeks_available,
            "can_do_trends": weeks_available >= 4,
            "can_do_seasonality": weeks_available >= 12,
            # Use earliest snapshot's period_start as stable baseline
            "baseline_date": snaps[0]["period_start"] if weeks_available >= 4 else None,
        }

    # ------------------------------------------------------------------
    def list_snapshots(self, analysis_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        if analysis_type:
            return self.db.get_snapshots_by_type(analysis_type, limit)
        # merge all
        snaps = []
        for t in ("weekly", "monthly", "quarterly"):
            snaps.extend(self.db.get_snapshots_by_type(t, limit))
        return sorted(snaps, key=lambda s: (s["period_start"] or date.min), reverse=True)[:limit]

    # ------------------------------------------------------------------
    # Async Methods for Non-Blocking Operations
    # ------------------------------------------------------------------
    
    async def save_snapshot_async(self, analysis_output: Dict[str, Any], analysis_type: str = "weekly") -> str:
        """Async wrapper for save_snapshot to prevent blocking the event loop.
        
        This is especially important for long-running DuckDB operations in async contexts.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.save_snapshot, analysis_output, analysis_type)
    
    async def get_prior_snapshot_async(self, current_snapshot_id: str, analysis_type: str = "weekly") -> Optional[Dict[str, Any]]:
        """Async wrapper for get_prior_snapshot."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_prior_snapshot, current_snapshot_id, analysis_type)
    
    async def list_snapshots_async(self, analysis_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Async wrapper for list_snapshots."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.list_snapshots, analysis_type, limit)
    
    async def get_historical_context_async(self) -> Dict[str, Any]:
        """Async wrapper for get_historical_context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_historical_context)
    
    # ------------------------------------------------------------------
    # JSON Schema Generation for API Documentation
    # ------------------------------------------------------------------
    
    @staticmethod
    def get_snapshot_json_schema(mode: str = 'validation') -> Dict[str, Any]:
        """Generate JSON schema for SnapshotData model.
        
        Args:
            mode: 'validation' or 'serialization' - determines schema focus
            
        Returns:
            JSON schema dict suitable for API documentation
        """
        return SnapshotData.model_json_schema(mode=mode)
    
    @staticmethod
    def get_comparison_json_schema() -> Dict[str, Any]:
        """Generate JSON schema for ComparisonData model."""
        return ComparisonData.model_json_schema()
    
    # ------------------------------------------------------------------
    def migrate_json_snapshots(self) -> Dict[str, int]:
        # Read base output directory from settings, fallback to hardcoded if absent
        try:
            base_output = getattr(settings, "output_directory", "outputs")
        except Exception:  # noqa: broad-except
            base_output = "outputs"
        outputs_dir = Path(base_output) / "historical_data"
        migrated = 0
        skipped = 0
        errors = 0
        for path in outputs_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                self.save_snapshot(data, data.get("snapshot_type", "weekly"))
                migrated += 1
            except Exception as exc:  # noqa: broad-except
                errors += 1
                logger.warning("Migration failed for %s: %s", path, exc)
        return {"migrated_count": migrated, "skipped_count": skipped, "error_count": errors}

    # ------------------------------------------------------------------
    # Internal helpers (kept simple for now)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_snapshot_date(snapshot_id: str) -> Optional[date]:
        m = re.search(r"_(\d{8})$", snapshot_id)
        if not m:
            return None
        return datetime.strptime(m.group(1), "%Y%m%d").date()

    @staticmethod
    def _generate_snapshot_id(dt: date, analysis_type: str) -> str:
        return f"{analysis_type}_{dt.strftime('%Y%m%d')}"

    # ----- extraction helpers --------------------------------------------------

    @staticmethod
    def _extract_topic_volumes(agent_results: Dict[str, Any]) -> Dict[str, int]:
        try:
            td = agent_results.get("TopicDetectionAgent", {})
            return td.get("data", {}).get("topic_distribution", {})
        except Exception:  # noqa: broad-except
            return {}

    @staticmethod
    def _extract_topic_sentiments(agent_results: Dict[str, Any]) -> Dict[str, Any]:
        try:
            proc = agent_results.get("TopicProcessingAgent", {})
            return proc.get("data", {}).get("topic_sentiments", {})
        except Exception:  # noqa: broad-except
            return {}

    @staticmethod
    def _extract_tier_distribution(agent_results: Dict[str, Any]) -> Dict[str, int]:
        try:
            seg = agent_results.get("SegmentationAgent", {})
            return seg.get("data", {}).get("tier_distribution", {})
        except Exception:  # noqa: broad-except
            return {}
