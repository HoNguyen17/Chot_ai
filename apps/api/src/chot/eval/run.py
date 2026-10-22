"""CLI đánh giá.

Ví dụ (chạy từ thư mục gốc repo, sau `make install`):
  # Baseline keyword vs đáp án — không cần API key
  python -m chot.eval.run --system keyword --gold data/answer_key

  # Pipeline chính (LLM + luật). Lưu sự kiện LLM để replay khi chỉ sửa luật.
  python -m chot.eval.run --system llm --gold data/gold --save data/runs

  # Họp dài L1–L4 (không áp MAX_TRANSCRIPT_CHARS của API)
  python -m chot.eval.run --system llm --transcripts data/long/raw --gold data/long/gold --save data/runs

  # Replay sự kiện LLM đã lưu qua luật mới (không tốn token)
  python -m chot.eval.run --system replay --events data/runs/<run>/events --gold data/gold

  # Đo độ đồng thuận: nhãn của bạn (data/gold) so với đáp án
  python -m chot.eval.run --system labels --pred data/gold --gold data/answer_key
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from chot.adapters.parsing import parse_transcript_file
from chot.domain.models import ExtractionResult, Ledger
from chot.eval.metrics import (
    Counts,
    GoldMeeting,
    ledger_as_gold,
    render_table,
    score_meeting,
    summarize,
)
from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor
from chot.usecases.ports import LedgerBuilder


def _load_gold(path: Path) -> GoldMeeting:
    return GoldMeeting.model_validate_json(path.read_text(encoding="utf-8"))


def _builder(args: argparse.Namespace) -> tuple[LedgerBuilder | None, object | None]:
    """Trả (builder, client LLM nếu có) — client giữ `usage` để tính chi phí."""
    if args.system == "keyword":
        from chot.adapters.baselines import KeywordBaseline

        return KeywordBaseline(), None
    if args.system in ("llm", "summary"):
        from chot.adapters.llm import OpenAICompatibleClient
        from chot.api.deps import make_extractor
        from chot.config import get_settings

        s = get_settings()
        client = OpenAICompatibleClient(
            model=s.llm_model, api_key=s.llm_api_key, base_url=s.llm_base_url
        )
        if args.system == "summary":
            from chot.adapters.baselines.summary_prompt import SummaryPromptBaseline

            return SummaryPromptBaseline(client), client
        # cùng composition với API: họp > CHUNK_SIZE câu → hai lượt (đổi qua biến env)
        print(f"CHUNK_SIZE={s.chunk_size}, CHUNK_CONTEXT={s.chunk_context}")
        return RulesLedgerBuilder(make_extractor(s, client)), client
    return None, None


def _with_cost(usage: dict) -> dict:
    """Chi phí USD theo PRICE_IN_PER_M / PRICE_OUT_PER_M (giá mỗi 1M token) trong .env."""
    price_in = float(os.environ.get("PRICE_IN_PER_M") or 0)
    price_out = float(os.environ.get("PRICE_OUT_PER_M") or 0)
    cost = (usage["prompt_tokens"] * price_in + usage["completion_tokens"] * price_out) / 1e6
    return {**usage, "cost_usd": round(cost, 4)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chốt — eval trên bộ test có bẫy")
    ap.add_argument(
        "--system", choices=["keyword", "summary", "llm", "replay", "labels"], required=True
    )
    ap.add_argument("--transcripts", default="data/raw", type=Path)
    ap.add_argument("--gold", default="data/gold", type=Path)
    ap.add_argument("--pred", type=Path, help="(labels) thư mục ledger/nhãn cần so")
    ap.add_argument("--events", type=Path, help="(replay) thư mục events/<meeting>.json")
    ap.add_argument("--save", type=Path, help="lưu ledger, sự kiện và báo cáo vào thư mục này")
    ap.add_argument("--only", nargs="*", help="chỉ chạy các meeting id này")
    ap.add_argument("--show-errors", action="store_true")
    args = ap.parse_args(argv)

    gold_files = sorted(p for p in args.gold.glob("*.json") if not p.name.startswith("TEMPLATE"))
    if args.only:
        gold_files = [p for p in gold_files if p.stem in args.only]
    if not gold_files:
        print(f"Không thấy file gold nào trong {args.gold}", file=sys.stderr)
        return 1

    run_dir = None
    if args.save:
        run_dir = args.save / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{args.system}"
        (run_dir / "ledgers").mkdir(parents=True)
        (run_dir / "events").mkdir()

    builder, client = _builder(args)
    total = Counts()
    per_meeting = {}
    usage_by_meeting: dict[str, dict] = {}
    for gpath in gold_files:
        gold = _load_gold(gpath)
        tpath = args.transcripts / f"{gold.meeting_id}.txt"
        tr = parse_transcript_file(tpath) if tpath.exists() else None

        if args.system == "labels":
            pred_path = args.pred / gpath.name
            if not pred_path.exists():
                print(f"  bỏ qua {gold.meeting_id}: không có {pred_path}")
                continue
            pred = _load_gold(pred_path)
            counts = score_meeting(pred, gold, None)
        else:
            if tr is None:
                print(f"  bỏ qua {gold.meeting_id}: không có transcript {tpath}")
                continue
            if args.system == "replay":
                extraction = ExtractionResult.model_validate_json(
                    (args.events / f"{gold.meeting_id}.json").read_text(encoding="utf-8")
                )
                builder = RulesLedgerBuilder(StaticExtractor(extraction))
            before = dict(client.usage) if client else None
            ledger: Ledger = builder.build(tr)
            counts = score_meeting(ledger_as_gold(ledger), gold, tr, ledger)
            if client:
                usage_by_meeting[gold.meeting_id] = {
                    k: client.usage[k] - before[k] for k in client.usage
                }
            if run_dir:
                (run_dir / "ledgers" / f"{gold.meeting_id}.json").write_text(
                    ledger.model_dump_json(indent=2), encoding="utf-8"
                )
                extraction = getattr(builder, "last_extraction", None)
                if extraction:
                    (run_dir / "events" / f"{gold.meeting_id}.json").write_text(
                        extraction.model_dump_json(indent=2), encoding="utf-8"
                    )
        per_meeting[gold.meeting_id] = summarize(counts)
        total.add(counts)

    summary = summarize(total)
    usage = _with_cost(client.usage) if client else None
    print(render_table(summary, f"{args.system} — {len(per_meeting)} cuộc họp"))
    if usage:
        print(
            f"\nToken: {usage['prompt_tokens']} vào / {usage['completion_tokens']} ra, "
            f"{usage['calls']} lần gọi, ~${usage['cost_usd']}"
        )
    if args.show_errors and total.errors:
        print("\nLỗi chi tiết:")
        for e in total.errors:
            print("  -", e)
    if run_dir:
        report = {
            "system": args.system,
            "summary": summary,
            "per_meeting": per_meeting,
            "usage": usage,
            "usage_by_meeting": usage_by_meeting,
            "errors": total.errors,
        }
        (run_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nĐã lưu: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
