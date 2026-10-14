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

export default function UploadPage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<MeetingSummary[]>([]);
  const [sample, setSample] = useState<{ id: string; text: string; title: string } | null>(null);
  const [code, setCode] = useState("");
  const isSample = sample !== null && text === sample.text;

  useEffect(() => {
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
        ? await api.createMeeting(text, sample.id)
        : await api.createMeeting(text, undefined, code.trim());
      router.push(`/meetings/${meeting.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xử lý được transcript.");
      setBusy(false);
    }
  }

  return (
    <>
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

      {recent.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Cuộc họp gần đây</h2>
          </div>
          {recent.map((m) => (
            <Link key={m.id} href={`/meetings/${m.id}`} className="card row" style={{ display: "flex", justifyContent: "space-between", textDecoration: "none" }}>
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
