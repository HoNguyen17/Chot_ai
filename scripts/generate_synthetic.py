"""Sinh transcript + nhãn gold NHÁP từ data/synthetic/scenarios.json.

    python scripts/generate_synthetic.py --only m06 m07
    python scripts/generate_synthetic.py            # cả 15 kịch bản

Đầu ra: data/synthetic/drafts/<id>.txt và <id>.gold.json
QUAN TRỌNG: đây là bản nháp. Đọc lại, sửa transcript cho tự nhiên, sửa nhãn theo
docs/LABELING_GUIDE.md, rồi mới chép sang data/raw/ và data/gold/.

Nên dùng một model KHÁC với model chạy pipeline (vd sinh bằng Claude, chạy pipeline bằng GPT/Qwen)
để tránh việc model tự chấm bài của chính nó.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from chot.adapters.llm.client import OpenAICompatibleClient  # noqa: E402
from chot.adapters.llm.event_extractor import load_prompt  # noqa: E402
from chot.adapters.parsing import parse_transcript  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--start-date", default="2026-10-12", help="ngày họp của m06; mỗi kịch bản +1 ngày")
    ap.add_argument("--model", default=os.environ.get("GEN_MODEL") or os.environ.get("LLM_MODEL"))
    args = ap.parse_args()

    spec = json.loads((ROOT / "data/synthetic/scenarios.json").read_text(encoding="utf-8"))
    glossary = spec["trap_glossary"]
    out = ROOT / "data/synthetic/drafts"
    out.mkdir(parents=True, exist_ok=True)

    client = OpenAICompatibleClient(
        model=args.model or "gpt-4.1-mini",
        api_key=os.environ.get("GEN_API_KEY") or os.environ.get("LLM_API_KEY"),
        base_url=os.environ.get("GEN_BASE_URL") or os.environ.get("LLM_BASE_URL"),
        temperature=0.8,
    )
    template = load_prompt("generate_transcript")
    start = dt.date.fromisoformat(args.start_date)

    for i, sc in enumerate(spec["scenarios"]):
        if args.only and sc["id"] not in args.only:
            continue
        date = start + dt.timedelta(days=i)
        traps = "\n".join(f"  - {t}: {glossary.get(t, t)}" for t in sc["traps"])
        prompt = (
            template.replace("{{ID}}", sc["id"])
            .replace("{{DOMAIN}}", sc["domain"])
            .replace("{{CHAIR}}", sc["chair"])
            .replace("{{PEOPLE}}", str(sc["people"]))
            .replace("{{DATE}}", date.isoformat())
            .replace("{{TRAPS}}", traps)
        )
        data = json.loads(client.complete_json(prompt, schema=None))
        transcript = data["transcript"].strip() + "\n"
        try:
            n = len(parse_transcript(transcript).utterances)
        except ValueError as e:
            print(f"✗ {sc['id']}: transcript sai định dạng — {e}")
            continue
        (out / f"{sc['id']}.txt").write_text(transcript, encoding="utf-8")
        (out / f"{sc['id']}.gold.json").write_text(
            json.dumps(data["gold"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"✓ {sc['id']}: {n} câu, {len(data['gold'].get('items', []))} mục nhãn nháp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
