"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MeetingSummary } from "@/lib/types";

export default function UploadPage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<MeetingSummary[]>([]);

  useEffect(() => {
    api.listMeetings().then(setRecent).catch(() => setRecent([]));
  }, []);

  async function loadFile(file: File) {
    setText(await file.text());
  }

  async function loadSample() {
    const res = await fetch("/samples/m01.txt");
    setText(await res.text());
  }

  async function submit() {
    if (!text.trim()) {
      setError("Dán transcript hoặc chọn file .txt trước.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const meeting = await api.createMeeting(text);
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
            <button className="btn btn-sm" onClick={loadSample}>
              Dùng transcript mẫu
            </button>
          </div>
          <button className="btn btn-primary" onClick={submit} disabled={busy}>
            {busy ? "Đang phân tích…" : "Chốt biên bản"}
          </button>
        </div>
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
