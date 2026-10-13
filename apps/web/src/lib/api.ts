import type { Meeting, MeetingSummary, Status } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  listMeetings: () => request<MeetingSummary[]>("/meetings"),
  getMeeting: (id: string) => request<Meeting>(`/meetings/${id}`),
  createMeeting: (transcript_text: string) =>
    request<Meeting>("/meetings", { method: "POST", body: JSON.stringify({ transcript_text }) }),
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
