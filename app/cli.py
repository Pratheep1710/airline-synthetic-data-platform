from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.dataset_service import DatasetService


async def generate_dataset(record_count: int, dataset_version: str | None, llm: bool) -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        service = DatasetService(db)
        job = await service.create_job(
            record_count=record_count,
            enable_llm_enrichment=llm,
            dataset_version=dataset_version or datetime.now(UTC).strftime("v%Y%m%d%H%M%S"),
        )
        print(json.dumps(service.to_job_response(job).model_dump(mode="json"), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Airline synthetic dataset CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Generate a synthetic dataset")
    gen.add_argument("--record-count", type=int, default=75)
    gen.add_argument("--dataset-version", type=str, default=None)
    gen.add_argument("--enable-llm-enrichment", action="store_true")
    args = parser.parse_args()

    if args.command == "generate":
        asyncio.run(
            generate_dataset(
                record_count=args.record_count,
                dataset_version=args.dataset_version,
                llm=args.enable_llm_enrichment,
            )
        )


if __name__ == "__main__":
    main()
