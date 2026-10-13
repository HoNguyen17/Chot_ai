"""Hai dạng xuất từ cùng một Ledger: biên bản họp (Markdown) và task list (CSV / JSON)."""

from __future__ import annotations

import csv
import io

from chot.domain.enums import ItemType, Status
from chot.domain.models import Item, Ledger, Transcript

STATUS_VI = {
    Status.FINAL: "Đã chốt",
    Status.NEEDS_CONFIRMATION: "Cần xác nhận",
    Status.SUPERSEDED: "Bị thay thế",
    Status.REJECTED: "Bị bác",
    Status.DEFERRED: "Hoãn",
    Status.OPEN: "Đang mở",
}


def _cite(item: Item) -> str:
    return ", ".join(f"[{e.ts or e.utt}]" for e in item.evidence)


def _line(item: Item) -> str:
    extra = []
    if item.owner:
        extra.append(f"phụ trách: {item.owner}")
    if item.deadline:
        extra.append(f"hạn: {item.deadline:%d/%m/%Y}")
    elif item.deadline_text:
        extra.append(f"hạn: {item.deadline_text}")
    if item.decided_by and item.type == ItemType.DECISION:
        verb = "chốt bởi" if item.status == Status.FINAL else "đồng ý bởi"
        extra.append(f"{verb}: {item.decided_by}")
    meta = f" — {'; '.join(extra)}" if extra else ""
    tag = "" if item.status in (Status.FINAL, Status.OPEN) else f"**[{STATUS_VI[item.status]}]** "
    return f"- {tag}{item.content}{meta} {_cite(item)}"


def to_markdown_minutes(tr: Transcript, ledger: Ledger) -> str:
    """Biên bản họp, cấu trúc tham khảo mẫu NĐ 30/2020: thành phần → kết luận → tồn đọng."""
    chair = ", ".join(p.name for p in tr.participants if p.is_chair) or "-"
    members = ", ".join(f"{p.name}" + (f" ({p.role})" if p.role else "") for p in tr.participants)
    start = tr.utterances[0].ts_label if tr.utterances else "-"
    end = tr.utterances[-1].ts_label if tr.utterances else "-"

    def section(title: str, items: list[Item]) -> str:
        body = "\n".join(_line(i) for i in items) or "- (không có)"
        return f"## {title}\n{body}\n"

    items = ledger.items
    decisions = [i for i in items if i.type == ItemType.DECISION and i.status == Status.FINAL]
    tasks = [i for i in items if i.type == ItemType.TASK and i.status == Status.OPEN]
    pending = [i for i in items if i.status in (Status.NEEDS_CONFIRMATION, Status.DEFERRED)]
    open_issues = [
        i
        for i in items
        if i.type in (ItemType.BLOCKER, ItemType.OPEN_QUESTION) and i.status == Status.OPEN
    ]
    notes = [
        i for i in items if i.type in (ItemType.KNOWLEDGE, ItemType.REQUEST, ItemType.FEEDBACK)
    ]
    history = [i for i in items if i.status == Status.SUPERSEDED]

    return "\n".join(
        [
            f"# BIÊN BẢN HỌP — {tr.title or tr.meeting_id}",
            "",
            f"- **Ngày:** {tr.date:%d/%m/%Y}" if tr.date else "- **Ngày:** -",
            f"- **Thời lượng ghi nhận:** {start} → {end}",
            f"- **Chủ trì:** {chair}",
            f"- **Thành phần:** {members}",
            f"- **Vắng mặt:** {', '.join(p.name for p in tr.absent) or 'không'}",
            "",
            section("1. Kết luận đã thống nhất", decisions),
            section("2. Phân công công việc", tasks),
            section("3. Vấn đề còn tồn đọng / cần xác nhận", pending),
            section("4. Vướng mắc & câu hỏi mở", open_issues),
            section("5. Ghi nhận khác (tri thức, yêu cầu, phản hồi)", notes),
            section("Phụ lục: phương án đã bị thay thế", history),
            "_Mỗi dòng có mốc thời gian trỏ về transcript. Biên bản do Chốt tạo, đã qua người duyệt._",
        ]
    )


def to_csv_tasks(ledger: Ledger) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "task", "owner", "deadline", "deadline_text", "status", "evidence"])
    for i in ledger.items:
        if i.type == ItemType.TASK:
            w.writerow(
                [
                    i.id,
                    i.content,
                    i.owner or "",
                    i.deadline or "",
                    i.deadline_text or "",
                    STATUS_VI[i.status],
                    _cite(i),
                ]
            )
    return buf.getvalue()


def to_json(ledger: Ledger) -> str:
    return ledger.model_dump_json(indent=2)
