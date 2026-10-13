import type { Meeting, MeetingSummary, Status } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Thông báo dự phòng khi API trả detail không phải chuỗi (vd. lỗi validate của pydantic).
const STATUS_MESSAGES: Record<number, string> = {
  413: "Transcript quá dài. Hãy cắt bớt rồi thử lại.",
  422: "Transcript không đúng định dạng [mm:ss] Tên: câu nói.",
  429: "Đã hết lượt phân tích bằng AI trong giờ này. Thử lại sau, hoặc chọn một transcript mẫu.",
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* body không phải JSON */
    }
    throw new Error(typeof detail === "string" ? detail : (STATUS_MESSAGES[res.status] ?? res.statusText));
  }
  return res.json() as Promise<T>;
}

export const api = {
  listMeetings: () => request<MeetingSummary[]>("/meetings"),
  getMeeting: (id: string) => request<Meeting>(`/meetings/${id}`),
  createMeeting: (transcript_text: string, meeting_id?: string) =>
    request<Meeting>("/meetings", {
      method: "POST",
      body: JSON.stringify({ transcript_text, meeting_id }),
    }),
  reviewItem: (
    id: string,
    itemId: string,
    changes: Partial<{ status: Status; owner: string | null; deadline: string | null; content: string; approved: boolean }>,
  ) =>
    request<Meeting>(`/meetings/${id}/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),
  publish: (id: string) => request<Meeting>(`/meetings/${id}/publish`, { method: "POST" }),
  exportUrl: (id: string, format: "md" | "csv" | "json") =>
    `${API_URL}/meetings/${id}/export?format=${format}`,
};
