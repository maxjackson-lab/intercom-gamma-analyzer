"""
Standalone verifier for Russian/Korean keyword coverage.

The script checks both TaxonomyManager classifications and the keyword-only
path inside TopicDetectionAgent to ensure multilingual support remains stable.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock

from rich.console import Console
from rich.table import Table

from src.config.taxonomy import TaxonomyManager
import src.agents.topic_detection_agent as topic_detection_module
from src.agents.topic_detection_agent import TopicDetectionAgent


console = Console(record=True)


def _ensure_mock_ai_client() -> None:
    """
    TopicDetectionAgent requires an AI client even if we only use keyword logic.
    For offline verification we stub the client + semaphore to avoid network calls.
    """
    if getattr(topic_detection_module, "_mlk_mock_applied", False):
        return

    mock_client = MagicMock(name="MockAIClient")
    mock_client.client = MagicMock()
    mock_client.max_tokens = 1
    mock_client.temperature = 0.1

    topic_detection_module.get_ai_client = lambda: mock_client  # type: ignore
    topic_detection_module.get_recommended_semaphore = lambda _client: asyncio.Semaphore(1)  # type: ignore
    topic_detection_module._mlk_mock_applied = True  # type: ignore[attr-defined]


def build_test_conversations() -> Dict[str, List[Dict[str, str]]]:
    return {
        "russian": [
            {
                "topic": "Account",
                "text": "Я не могу войти в свой аккаунт. Забыл пароль.",
            },
            {
                "topic": "Billing",
                "text": "Хочу получить возврат денег за подписку.",
            },
            {
                "topic": "Bug",
                "text": "У меня ошибка при экспорте файла.",
            },
        ],
        "korean": [
            {
                "topic": "Account",
                "text": "계정에 로그인할 수 없습니다. 비밀번호를 잊어버렸어요.",
            },
            {
                "topic": "Billing",
                "text": "구독 환불을 원합니다.",
            },
            {
                "topic": "Bug",
                "text": "파일 내보내기 오류가 있습니다.",
            },
        ],
    }


def create_conversation_payload(text: str) -> Dict:
    return {
        "id": f"mlk-{hash(text)}",
        "source": {"author": {"id": "user_1", "name": "Test User"}},
        "conversation_parts": {"conversation_parts": []},
        "custom_attributes": {},
        "body": text,
    }


async def detect_with_keywords(agent: TopicDetectionAgent, conversation: Dict) -> str:
    results = await agent._fallback_to_keywords(conversation)
    return results[0]["topic"] if results else "Unknown/unresponsive"


def run_evaluation(language: str, save_results: bool, output_dir: Path, verbose: bool) -> Dict:
    _ensure_mock_ai_client()
    taxonomy = TaxonomyManager()
    agent = TopicDetectionAgent(llm_first=False)

    samples = build_test_conversations()
    selected_languages = [language] if language in samples else list(samples.keys())

    table = Table(title="Multi-language Keyword Verification")
    table.add_column("Language", justify="center")
    table.add_column("Expected Topic", justify="center")
    table.add_column("Detected (Taxonomy)", justify="center")
    table.add_column("Detected (Agent)", justify="center")
    table.add_column("Confidence", justify="center")
    table.add_column("Method", justify="center")

    results: List[Dict] = []

    for lang in selected_languages:
        for sample in samples[lang]:
            conversation = create_conversation_payload(sample["text"])
            classification = taxonomy.classify_conversation(conversation)
            taxonomy_topic = classification[0]["category"] if classification else "None"
            confidence = classification[0]["confidence"] if classification else 0.0
            agent_topic = asyncio.run(detect_with_keywords(agent, conversation))
            method = classification[0]["method"] if classification else "n/a"
            success = taxonomy_topic == sample["topic"] and agent_topic == sample["topic"]

            results.append(
                {
                    "language": lang,
                    "expected_topic": sample["topic"],
                    "taxonomy_topic": taxonomy_topic,
                    "agent_topic": agent_topic,
                    "confidence": confidence,
                    "method": method,
                    "success": success,
                    "text": sample["text"],
                }
            )

            console.log(
                f"[{'green' if success else 'red'}]({lang}) {sample['text'][:30]}... => taxonomy={taxonomy_topic}, agent={agent_topic}, confidence={confidence:.2f}"
            )
            table.add_row(
                lang.title(),
                sample["topic"],
                taxonomy_topic,
                agent_topic,
                f"{confidence:.2f}",
                method,
            )

    console.print(table)

    summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "language_filter": language,
        "total_cases": len(results),
        "success_count": sum(1 for r in results if r["success"]),
        "failures": [r for r in results if not r["success"]],
        "results": results,
    }

    if save_results:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"multi_language_test_results_{timestamp}.json"
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)
        log_path = output_dir / f"multi_language_test_{timestamp}.log"
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(console.export_text(clear=False))
        console.print(f"[bold green]Saved JSON report to {json_path}[/bold green]")
        console.print(f"[bold green]Saved log to {log_path}[/bold green]")

    if verbose:
        console.print(summary)

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify multi-language keyword detection.")
    parser.add_argument(
        "--language",
        choices=["russian", "korean", "all"],
        default="all",
        help="Language subset to test.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose JSON summary.",
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        default=True,
        help="Persist JSON + log artifacts (default: True).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./test_outputs"),
        help="Directory for saved artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    language = "all" if args.language == "all" else args.language
    run_evaluation(language, args.save_results, args.output_dir, args.verbose)


if __name__ == "__main__":
    main()

