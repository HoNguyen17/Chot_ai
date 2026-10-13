from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from chot import __version__
from chot.adapters.export import to_csv_tasks, to_json, to_markdown_minutes
from chot.adapters.parsing.transcript_txt import TranscriptParseError
from chot.api.deps import RateLimitExceeded, client_ip, get_service
from chot.api.schemas import CreateMeetingIn, MeetingOut, MeetingSummaryOut, ReviewItemIn
from chot.config import get_settings
from chot.domain.enums import Status
from chot.usecases.meetings import MeetingService

Svc = Annotated[MeetingService, Depends(get_service)]


def create_app() -> FastAPI:
    app = FastAPI(title="Chốt API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(get_settings().cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health(svc: Svc) -> dict:
        return {"ok": True, "version": __version__, "builder": svc.builder.name}

    @app.post("/meetings", response_model=MeetingOut, status_code=201)
    def create_meeting(body: CreateMeetingIn, request: Request, svc: Svc):
        limit, size = get_settings().max_transcript_chars, len(body.transcript_text)
        if size > limit:
            msg = f"Transcript dài {size:,} ký tự (tối đa {limit:,}). Hãy cắt bớt rồi thử lại."
            raise HTTPException(413, msg.replace(",", "."))
        # Endpoint sync: builder chạy cùng thread nên đọc được IP này.
        client_ip.set(request.client.host if request.client else "?")
        try:
            record = svc.process(body.transcript_text, body.meeting_id)
        except TranscriptParseError as e:
            raise HTTPException(422, str(e)) from e
        except RateLimitExceeded as e:
            raise HTTPException(
                429,
                "Đã hết lượt phân tích bằng AI trong giờ này. Thử lại sau, "
                "hoặc chọn một transcript mẫu (không giới hạn).",
            ) from e
        return MeetingOut.from_record(record)

    @app.get("/meetings", response_model=list[MeetingSummaryOut])
    def list_meetings(svc: Svc):
        return [
            MeetingSummaryOut(
                id=r.id,
                title=r.transcript.title,
                date=r.transcript.date,
                items=len(r.ledger.items),
                needs_confirmation=len(r.ledger.by_status(Status.NEEDS_CONFIRMATION)),
                published=r.published,
            )
            for r in svc.repo.list()
        ]

    @app.get("/meetings/{meeting_id}", response_model=MeetingOut)
    def get_meeting(meeting_id: str, svc: Svc):
        record = svc.repo.get(meeting_id)
        if not record:
            raise HTTPException(404, "Không tìm thấy cuộc họp")
        return MeetingOut.from_record(record)

    @app.patch("/meetings/{meeting_id}/items/{item_id}", response_model=MeetingOut)
    def review_item(meeting_id: str, item_id: str, body: ReviewItemIn, svc: Svc):
        try:
            record = svc.review_item(meeting_id, item_id, body.changes())
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        return MeetingOut.from_record(record)

    @app.post("/meetings/{meeting_id}/publish", response_model=MeetingOut)
    def publish(meeting_id: str, svc: Svc):
        try:
            record = svc.publish(meeting_id)
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        except ValueError as e:
            raise HTTPException(409, str(e)) from e
        return MeetingOut.from_record(record)

    @app.get("/meetings/{meeting_id}/export")
    def export(
        meeting_id: str,
        svc: Svc,
        format: Annotated[str, Query(pattern="^(md|json|csv)$")] = "md",
    ):
        record = svc.repo.get(meeting_id)
        if not record:
            raise HTTPException(404, "Không tìm thấy cuộc họp")
        if format == "md":
            body, media = to_markdown_minutes(record.transcript, record.ledger), "text/markdown"
        elif format == "csv":
            body, media = to_csv_tasks(record.ledger), "text/csv"
        else:
            body, media = to_json(record.ledger), "application/json"
        filename = f"chot-{meeting_id}.{format}"
        return PlainTextResponse(
            body,
            media_type=f"{media}; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app


app = create_app()
