from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from chot import __version__
from chot.adapters.export import to_csv_tasks, to_json, to_markdown_minutes
from chot.adapters.parsing.transcript_txt import TranscriptParseError
from chot.api.deps import (
    AccessDenied,
    RateLimiter,
    RateLimitExceeded,
    access_code,
    client_ip,
    get_service,
)
from chot.api.schemas import (
    AnswerIn,
    CreateMeetingIn,
    CreateSeriesIn,
    MeetingOut,
    MeetingSummaryOut,
    ReviewItemIn,
    SeriesOut,
)
from chot.config import get_settings
from chot.usecases.meetings import MeetingRecord, MeetingService, Published, ReadOnly

Svc = Annotated[MeetingService, Depends(get_service)]


def create_app() -> FastAPI:
    settings = get_settings()
    hide_docs = {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(
        title="Chốt API", version=__version__, **(hide_docs if settings.public_demo else {})
    )
    # Mỗi ký tự có thể bị JSON escape thành 6 byte (\uXXXX) + phần dư cho field khác.
    max_body = settings.max_transcript_chars * 6 + 1024

    @app.middleware("http")
    async def limit_body(request: Request, call_next):
        # ponytail: chỉ chặn theo Content-Length; body chunked không có header vẫn lọt.
        if int(request.headers.get("content-length") or 0) > max_body:
            return JSONResponse({"detail": "Yêu cầu quá lớn. Hãy cắt bớt transcript."}, 413)
        return await call_next(request)

    # Thêm sau → bọc ngoài middleware trên, nên phản hồi 413 vẫn có header CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health(svc: Svc) -> dict:
        return {"ok": True, "version": __version__, "builder": svc.builder.name}

    def _ip(request: Request) -> str:
        return request.client.host if request.client else "?"

    def _create(
        body: CreateMeetingIn, request: Request, svc: MeetingService, series_id: str | None = None
    ) -> MeetingOut:
        limit, size = get_settings().max_transcript_chars, len(body.transcript_text)
        if size > limit:
            msg = f"Transcript dài {size:,} ký tự (tối đa {limit:,}). Hãy cắt bớt rồi thử lại."
            raise HTTPException(413, msg.replace(",", "."))
        # Endpoint sync: builder chạy cùng thread nên đọc được IP và mã này.
        client_ip.set(_ip(request))
        access_code.set(request.headers.get("x-access-code", ""))
        try:
            record = svc.process(body.transcript_text, body.meeting_id, series_id)
        except KeyError as e:
            raise HTTPException(404, e.args[0]) from e
        except ReadOnly as e:
            raise HTTPException(403, str(e)) from e
        except TranscriptParseError as e:
            raise HTTPException(422, str(e)) from e
        except AccessDenied as e:
            raise HTTPException(
                401,
                "Transcript mới cần mã truy cập để phân tích bằng AI. Transcript mẫu không cần mã.",
            ) from e
        except RateLimitExceeded as e:
            raise HTTPException(
                429,
                "Đã hết lượt phân tích bằng AI trong giờ này. Thử lại sau, "
                "hoặc chọn một transcript mẫu (không giới hạn).",
            ) from e
        return MeetingOut.from_record(record)

    @app.post("/meetings", response_model=MeetingOut, status_code=201)
    def create_meeting(body: CreateMeetingIn, request: Request, svc: Svc):
        return _create(body, request, svc)

    # trần toàn cục = 10 IP tạo hết lượt cùng giờ
    series_limiter = RateLimiter(
        settings.series_rate_limit_per_hour, settings.series_rate_limit_per_hour * 10
    )

    @app.post("/series", response_model=SeriesOut, status_code=201)
    def create_series(body: CreateSeriesIn, request: Request, svc: Svc):
        try:
            series_limiter.hit(_ip(request))
        except RateLimitExceeded as e:
            raise HTTPException(429, "Đã tạo quá nhiều nhóm họp trong giờ này. Thử lại sau.") from e
        return SeriesOut(**svc.create_series(body.name).model_dump())

    @app.get("/series/{series_id}", response_model=SeriesOut)
    def get_series(series_id: str, svc: Svc):
        try:
            return SeriesOut.from_view(svc.series_view(series_id))
        except KeyError as e:
            raise HTTPException(404, e.args[0]) from e

    @app.post("/series/{series_id}/meetings", response_model=MeetingOut, status_code=201)
    def create_series_meeting(series_id: str, body: CreateMeetingIn, request: Request, svc: Svc):
        return _create(body, request, svc, series_id)

    def list_meetings(svc: Svc):
        # Không liệt kê cuộc họp của nhóm họp: chúng chỉ mở bằng link bí mật của nhóm
        return [MeetingSummaryOut.from_record(r) for r in svc.repo.list() if not r.series_id]

    if not settings.public_demo:  # demo công khai: không lộ cuộc họp của người khác
        app.get("/meetings", response_model=list[MeetingSummaryOut])(list_meetings)

    @app.get("/meetings/{meeting_id}", response_model=MeetingOut)
    def get_meeting(meeting_id: str, svc: Svc):
        record = svc.repo.get(meeting_id)
        if not record:
            raise HTTPException(404, "Không tìm thấy cuộc họp")
        return MeetingOut.from_record(record)

    def _write(fn: Callable[[], MeetingRecord], invalid: int = 422) -> MeetingOut:
        """Chạy thao tác ghi lên một cuộc họp, đổi lỗi use case thành mã HTTP."""
        try:
            return MeetingOut.from_record(fn())
        except KeyError as e:
            raise HTTPException(404, e.args[0]) from e
        except ReadOnly as e:
            raise HTTPException(403, str(e)) from e
        except Published as e:
            raise HTTPException(409, str(e)) from e
        except ValueError as e:
            raise HTTPException(invalid, str(e)) from e

    @app.patch("/meetings/{meeting_id}/items/{item_id}", response_model=MeetingOut)
    def review_item(meeting_id: str, item_id: str, body: ReviewItemIn, svc: Svc):
        return _write(lambda: svc.review_item(meeting_id, item_id, body.changes()))

    @app.post("/meetings/{meeting_id}/items/{item_id}/answer", response_model=MeetingOut)
    def answer(meeting_id: str, item_id: str, body: AnswerIn, svc: Svc):
        return _write(
            lambda: svc.answer(
                meeting_id, item_id, body.action, body.owner, body.deadline, body.thread
            )
        )

    @app.post("/meetings/{meeting_id}/publish", response_model=MeetingOut)
    def publish(meeting_id: str, svc: Svc):
        return _write(lambda: svc.publish(meeting_id), invalid=409)

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
