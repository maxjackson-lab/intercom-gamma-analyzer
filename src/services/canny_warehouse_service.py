"""
Snowflake-backed access to historic Canny feedback.

This service fetches Canny posts from the analytics warehouse so they can be
normalized into the same conversation structure used by Intercom pipelines.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import snowflake.connector  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    snowflake = None
else:
    snowflake = snowflake.connector

from src.config.settings import settings


class SnowflakeNotConfiguredError(RuntimeError):
    """Raised when Snowflake credentials are missing."""


class CannyWarehouseService:
    """
    Thin wrapper around Snowflake queries for Canny feedback.

    The service is intentionally defensive: if credentials or the connector are
    missing we simply mark the service as disabled so callers can fall back to
    API-based Canny ingestion.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.table_identifier = self._build_table_identifier()
        self.enabled = all(
            [
                snowflake is not None,
                settings.snowflake_account,
                settings.snowflake_user,
                settings.snowflake_password,
                settings.snowflake_warehouse,
                settings.snowflake_database,
                settings.snowflake_schema,
                self.table_identifier,
            ]
        )

    # --------------------------------------------------------------------- API
    async def fetch_conversations(
        self,
        start_date: datetime,
        end_date: datetime,
        board_slug: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts in the requested window and normalize them to Intercom-style
        conversations so downstream TopicOrchestrator flows can consume them
        without any special handling.
        """

        posts = await self.fetch_posts(start_date, end_date, board_slug, limit)
        return [self._post_to_conversation(post) for post in posts]

    async def fetch_posts(
        self,
        start_date: datetime,
        end_date: datetime,
        board_slug: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Return normalized Snowflake rows (title/body/tags/etc.)."""

        if not self.enabled:
            raise SnowflakeNotConfiguredError(
                "Snowflake connection not configured. "
                "Set SNOWFLAKE_* env vars to enable warehouse-backed Canny data."
            )

        if limit <= 0:
            limit = 1000

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_posts_sync,
            start_date,
            end_date,
            board_slug,
            limit,
        )

    # ----------------------------------------------------------------- Internal
    def _fetch_posts_sync(
        self,
        start_date: datetime,
        end_date: datetime,
        board_slug: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        cursor = conn.cursor()

        query = f"""
            SELECT
                COALESCE(post_id, id)        AS post_id,
                title,
                body,
                status,
                board_slug,
                board_name,
                tags,
                created_at,
                updated_at,
                upvote_count,
                comment_count
            FROM {self.table_identifier}
            WHERE created_at BETWEEN %s AND %s
            {"AND board_slug = %s" if board_slug else ""}
            ORDER BY created_at DESC
            LIMIT {int(limit)}
        """

        params: List[Any] = [
            start_date.strftime("%Y-%m-%d %H:%M:%S"),
            end_date.strftime("%Y-%m-%d %H:%M:%S"),
        ]
        if board_slug:
            params.append(board_slug)

        try:
            cursor.execute(query, params)
            columns = [col[0].lower() for col in cursor.description]
            rows = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        normalized: List[Dict[str, Any]] = []
        for row in rows:
            record = {columns[idx]: row[idx] for idx in range(len(columns))}
            normalized.append(
                {
                    "post_id": record.get("post_id"),
                    "title": record.get("title"),
                    "body": record.get("body"),
                    "status": record.get("status"),
                    "board_slug": record.get("board_slug"),
                    "board_name": record.get("board_name"),
                    "tags": self._parse_tags(record.get("tags")),
                    "created_at": record.get("created_at"),
                    "updated_at": record.get("updated_at"),
                    "upvote_count": record.get("upvote_count") or 0,
                    "comment_count": record.get("comment_count") or 0,
                }
            )

        self.logger.info(
            "Fetched %s Canny posts from Snowflake", len(normalized)
        )
        return normalized

    def _connect(self):
        if snowflake is None:
            raise SnowflakeNotConfiguredError(
                "snowflake-connector-python is not installed."
            )

        return snowflake.connect(
            account=settings.snowflake_account,
            user=settings.snowflake_user,
            password=settings.snowflake_password,
            warehouse=settings.snowflake_warehouse,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            role=settings.snowflake_role,
        )

    @staticmethod
    def _parse_tags(raw_value: Any) -> List[str]:
        if raw_value is None:
            return []
        if isinstance(raw_value, list):
            return [str(item).strip() for item in raw_value if item]
        # Some warehouses store tags as comma-delimited strings
        return [tag.strip() for tag in str(raw_value).split(",") if tag.strip()]

    @staticmethod
    def _post_to_conversation(post: Dict[str, Any]) -> Dict[str, Any]:
        title = (post.get("title") or "").strip()
        body = (post.get("body") or "").strip()
        combined_body = "\n\n".join([seg for seg in [title, body] if seg])

        custom_attributes = {
            "canny_board": post.get("board_slug"),
            "canny_board_name": post.get("board_name"),
            "canny_status": post.get("status"),
            "canny_tags": post.get("tags"),
            "canny_upvotes": post.get("upvote_count"),
            "canny_comment_count": post.get("comment_count"),
        }

        return {
            "id": f"canny_{post.get('post_id')}",
            "source": {
                "type": "canny",
                "id": post.get("post_id"),
                "author": {"type": "user", "name": "Canny Feedback"},
            },
            "created_at": post.get("created_at"),
            "updated_at": post.get("updated_at"),
            "subject": title,
            "body": combined_body,
            "custom_attributes": custom_attributes,
            "metadata": {
                "source_system": "canny",
                "board_slug": post.get("board_slug"),
                "board_name": post.get("board_name"),
            },
            "conversation_parts": {"conversation_parts": []},
        }

    def _build_table_identifier(self) -> Optional[str]:
        table = settings.snowflake_canny_table
        if not table:
            return None

        if "." in table:
            return table

        parts: List[str] = []
        if settings.snowflake_database:
            parts.append(settings.snowflake_database)
        if settings.snowflake_schema:
            parts.append(settings.snowflake_schema)
        parts.append(table)
        return ".".join(parts)

