"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MeetingSummary } from "@/lib/types";

// Transcript mẫu (bản sao data/raw) — API replay output LLM đã lưu, không tốn token.
const SAMPLES = Array.from({ length: 25 }, (_, i) => `m${String(i + 1).padStart(2, "0")}`);
// Mã truy cập để gọi LLM — chỉ nhớ trong tab hiện tại.
const CODE_KEY = "chot-access-code";
const SAMPLE_SERIES = "mau-chot-m01-m05";

export default function UploadPage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<MeetingSummary[]>([]);
  const [sample, setSample] = useState<{ id: string; text: string; title: string } | null>(null);
  const [code, setCode] = useState("");
  const [seriesId, setSeriesId] = useState<string | undefined>();
  const [seriesName, setSeriesName] = useState("");
  const isSample = sample !== null && text === sample.text;

  useEffect(() => {
    // "+ Buổi họp mới" từ trang nhóm → /?series=<id>
    setSeriesId(new URLSearchParams(window.location.search).get("series") ?? undefined);
    api.listMeetings().then(setRecent).catch(() => setRecent([]));
    try {
      setCode(sessionStorage.getItem(CODE_KEY) ?? "");
    } catch {
      /* sessionStorage bị chặn */
    }
  }, []);

  function changeCode(value: string) {
    setCode(value);
    try {
      sessionStorage.setItem(CODE_KEY, value);
    } catch {
      /* sessionStorage bị chặn */
    }
  }

  async function loadFile(file: File) {
    setText(await file.text());
  }

  async function loadSample(id: string) {
    if (!id) return;
    const res = await fetch(`/samples/${id}.txt`);
    const body = await res.text();
    const title = body.match(/^# title:\s*(.+)$/m)?.[1] ?? id;
    setSample({ id, text: body, title });
    setText(body);
  }

  async function submit() {
    if (!text.trim()) {
      setError("Dán transcript hoặc chọn file .txt trước.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // Chỉ gửi meeting_id khi transcript mẫu chưa bị sửa — sửa rồi thì để LLM xử lý (cần mã).
      const meeting = isSample
        ? await api.createMeeting(text, sample.id, undefined, seriesId)
        : await api.createMeeting(text, undefined, code.trim(), seriesId);
      router.push(`/m/${meeting.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xử lý được transcript.");
      setBusy(false);
    }
  }

  async function createSeries() {
    setBusy(true);
    setError(null);
    try {
      const series = await api.createSeries(seriesName.trim());
      router.push(`/s/${series.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tạo được nhóm họp.");
      setBusy(false);
    }
  }

  return (
    <>
      {seriesId && (
        <p className="faint">
          Thêm buổi họp vào <Link href={`/s/${seriesId}`}>nhóm họp</Link>
        </p>
      )}
      <h1>Họp xong rồi. Giờ chốt lại.</h1>
      <p className="muted">
        Dán transcript cuộc họp. Chốt tìm ra điều gì <b>thật sự đã chốt</b>, ai làm gì, hạn nào và
        điều gì còn treo — mỗi dòng trỏ về đúng câu nói.
      </p>

      <div className="card" style={{ marginTop: 24 }}>
        <label htmlFor="transcript" className="faint">
          Transcript (.txt) — định dạng <span className="mono">[mm:ss] Tên: câu nói</span>
        </label>
        <textarea
          id="transcript"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={"# participants: Hùng (CEO, chủ trì); Minh (PM)\n[00:01:05] Minh: Em đề xuất VNPay…"}
          style={{ marginTop: 8 }}
        />
        <div className="row" style={{ marginTop: 12, justifyContent: "space-between" }}>
          <div className="row">
            <label className="btn btn-sm">
              Chọn file .txt
              <input
                type="file"
                accept=".txt,text/plain"
                hidden
                onChange={(e) => e.target.files?.[0] && loadFile(e.target.files[0])}
              />
            </label>
            <select
              aria-label="Dùng transcript mẫu"
              value={sample?.id ?? ""}
              onChange={(e) => loadSample(e.target.value)}
            >
              <option value="">Dùng transcript mẫu…</option>
              {SAMPLES.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={submit} disabled={busy}>
            {busy ? "Đang phân tích…" : "Chốt biên bản"}
          </button>
        </div>
        {!isSample && (
          <div style={{ marginTop: 12 }}>
            <label htmlFor="access-code" className="faint">
              Mã truy cập — transcript mới được phân tích bằng AI nên cần mã; transcript mẫu thì không
            </label>
            <input
              id="access-code"
              type="password"
              autoComplete="off"
              value={code}
              onChange={(e) => changeCode(e.target.value)}
              style={{ display: "block", marginTop: 8 }}
            />
          </div>
        )}
        {isSample && (
          <p className="faint" style={{ marginTop: 12 }}>
            <b>{sample.title}</b> — kết quả mẫu là output đã lưu của LLM (gpt-4.1-mini, ngày
            14/10/2026), không phải đáp án.
          </p>
        )}
        <p className="faint" style={{ marginTop: 8 }}>
          Bản demo: đừng dán nội dung cuộc họp thật.
        </p>
        {error && (
          <p className="alert" role="alert" style={{ marginTop: 12 }}>
            {error}
          </p>
        )}
      </div>

      {!seriesId && (
        <section className="section" aria-labelledby="h-series">
          <div className="section-head">
            <h2 id="h-series">Họp định kỳ?</h2>
          </div>
          <form
            className="card row"
            onSubmit={(e) => {
              e.preventDefault();
              if (seriesName.trim()) createSeries();
            }}
          >
            <input
              type="text"
              aria-label="Tên nhóm họp"
              placeholder="Tên nhóm họp, vd. Weekly sync App Giao Nhanh"
              maxLength={200}
              value={seriesName}
              onChange={(e) => setSeriesName(e.target.value)}
              style={{ flex: "1 1 240px", width: "auto" }}
            />
            <button className="btn" disabled={busy || !seriesName.trim()}>
              Tạo nhóm họp
            </button>
          </form>
          <p className="faint" style={{ marginTop: 8 }}>
            Nhóm gom các buổi họp, Kho tri thức và việc treo vào một link bí mật. Xem thử{" "}
            <Link href={`/s/${SAMPLE_SERIES}`}>nhóm mẫu m01–m05</Link>.
          </p>
        </section>
      )}

      {recent.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Cuộc họp gần đây</h2>
          </div>
          {recent.map((m) => (
            <Link key={m.id} href={`/m/${m.id}`} className="card row" style={{ display: "flex", justifyContent: "space-between", textDecoration: "none" }}>
              <span>
                <b>{m.title ?? m.id}</b> <span className="faint">{m.date}</span>
              </span>
              <span className="faint">
                {m.published ? "Đã xuất bản" : `${m.needs_confirmation} mục cần xác nhận`}
              </span>
            </Link>
          ))}
        </section>
      )}
    </>
  );
}
