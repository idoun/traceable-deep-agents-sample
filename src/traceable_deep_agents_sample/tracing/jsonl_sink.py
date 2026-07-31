import json
from pathlib import Path

from traceable_deep_agents_sample.tracing.events import TraceEvent


class JsonlTraceSink:
    def __init__(self, trace_dir: Path, run_id: str):
        self.path = trace_dir / f"{run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: TraceEvent) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")

