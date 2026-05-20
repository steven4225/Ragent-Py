from __future__ import annotations

import argparse
import time

from ragent_python.config import get_settings
from ragent_python.worker.ingestion_worker import run_ingestion_worker


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Ragent Python ingestion worker.")
    parser.add_argument("--once", action="store_true", help="Process one worker cycle and exit.")
    parser.add_argument("--limit", type=int, default=None, help="Override the per-cycle batch size.")
    parser.add_argument(
        "--task-id",
        action="append",
        dest="task_ids",
        default=[],
        help="Restrict worker execution to one or more specific task ids.",
    )
    args = parser.parse_args()

    settings = get_settings()
    batch_size = args.limit if args.limit is not None else settings.ingestion_worker_batch_size

    if args.once:
        result = run_ingestion_worker(limit=batch_size, task_ids=args.task_ids)
        print(
            f"[worker] processed={len(result.processedTaskIds)} "
            f"succeeded={len(result.succeededTaskIds)} failed={len(result.failedTaskIds)} "
            f"skipped={len(result.skippedTaskIds)} ids={','.join(result.processedTaskIds) or '-'}"
        )
        return

    poll_seconds = max(settings.ingestion_worker_poll_ms, 100) / 1000
    print(f"[worker] starting loop with batch_size={batch_size} poll_interval={poll_seconds:.2f}s")
    while True:
        result = run_ingestion_worker(limit=batch_size, task_ids=args.task_ids or None)
        if result.processedTaskIds:
            print(
                f"[worker] processed={len(result.processedTaskIds)} "
                f"succeeded={len(result.succeededTaskIds)} failed={len(result.failedTaskIds)} "
                f"ids={','.join(result.processedTaskIds)}"
            )
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
