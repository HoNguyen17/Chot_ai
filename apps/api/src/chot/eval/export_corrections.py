"""Xuất các lần người duyệt sửa sai (SPEC M3 §5.3) → data/corrections/<meeting>.json.

Chỉ để Nash gán nhãn lại / thêm case kiểm thử. KHÔNG nạp vào prompt (luật vàng #5).
Chạy: python -m chot.eval.export_corrections --out data/corrections   (đọc DATABASE_URL)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from chot.domain.enums import ReviewAction
from chot.usecases.meetings import MeetingRecord, MeetingRepository, ReviewLogEntry

CORRECTABLE_FIELDS = {"owner", "deadline", "content"}


def is_correction(e: ReviewLogEntry) -> bool:
    """Người duyệt sửa kết quả của máy: bác bỏ, hoặc đổi owner / hạn / nội dung đã có.

    Điền chỗ trống khi trả lời câu hỏi (owner/hạn đang None) không phải máy sai.
    """
    if e.action == ReviewAction.REJECT:
        return e.field == "status"  # 1 case / lần bác bỏ
    return e.field in CORRECTABLE_FIELDS and (e.action is None or e.old is not None)


def cases(record: MeetingRecord) -> list[dict[str, object]]:
    items = {i.id: i for i in record.ledger.items}
    return [
        {
            "meeting_id": record.id,
            "source_id": record.transcript.meeting_id,
            "item": items[e.item_id].model_dump(mode="json"),
            "evidence": [ev.model_dump(mode="json") for ev in items[e.item_id].evidence],
            **e.model_dump(mode="json", include={"field", "old", "new", "action", "by", "at"}),
        }
        for e in record.review_log
        if is_correction(e) and e.item_id in items
    ]


def export_corrections(repo: MeetingRepository, out: Path) -> int:
    """Ghi mỗi cuộc họp có sửa sai thành 1 file; trả về tổng số case."""
    out.mkdir(parents=True, exist_ok=True)
    total = 0
    for record in repo.list():
        if found := cases(record):
            (out / f"{record.id}.json").write_text(
                json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            total += len(found)
    return total


def main() -> None:
    from chot.api.deps import make_repo
    from chot.config import get_settings

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("data/corrections"))
    args = ap.parse_args()
    # Chỉ in số lượng — nội dung họp chỉ nằm trong file.
    print(f"{export_corrections(make_repo(get_settings()), args.out)} case → {args.out}")


if __name__ == "__main__":
    main()
