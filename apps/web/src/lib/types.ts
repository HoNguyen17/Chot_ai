// Đồng bộ với apps/api/src/chot/domain/models.py — sửa một bên thì sửa cả hai.

export type ItemType =
  | "decision"
  | "option"
  | "task"
  | "blocker"
  | "open_question"
  | "knowledge"
  | "request"
  | "feedback";

export type Status =
  | "final"
  | "needs_confirmation"
  | "superseded"
  | "rejected"
  | "deferred"
  | "open"
  | "noted"; // M3: tri thức, phản hồi

// M3 — trạng thái duyệt, tách khỏi Status
export type ReviewState = "auto_accepted" | "pending" | "confirmed" | "rejected" | "deferred";

// M3 — mã lý do (apps/api/src/chot/domain/reasons.py); câu hỏi sinh từ code + params
export type ReasonCode =
  | "NOT_CHAIR"
  | "HEDGED"
  | "NOD_ONLY"
  | "CO_CHAIR_OBJECTION"
  | "OWNER_MISSING"
  | "OWNER_UNCONFIRMED"
  | "OWNER_DECLINED"
  | "OWNER_ABSENT"
  | "DEADLINE_VAGUE"
  | "DURABLE_KNOWLEDGE"
  | "THREAD_UNMAPPED"
  | "FALLBACK_KEPT"
  | "CHANGED_MIND"
  | "NO_AGREEMENT"
  | "AGREEMENT_REVERSED";

export interface Reason {
  code: ReasonCode;
  params: Record<string, string | boolean | null>;
}

export interface TimelineEntry {
  utt: string;
  ts: string | null;
  speaker: string;
  kind: string;
  key: string | null;
  quote: string;
}

export interface Participant {
  name: string;
  role: string | null;
  is_chair: boolean;
}

export interface Utterance {
  id: string;
  index: number;
  ts: number;
  speaker: string;
  text: string;
}

export interface Evidence {
  utt: string | null; // null khi kind = "reviewer"
  quote: string;
  ts: string | null;
  speaker: string | null;
  kind: "transcript" | "reviewer";
  by: string | null;
  at: string | null;
  note: string | null;
}

export interface Item {
  id: string;
  type: ItemType;
  thread: string | null;
  content: string;
  status: Status;
  status_label: string; // nhãn theo type, từ bảng của API (status_table.py)
  owner: string | null;
  decided_by: string | null;
  deadline: string | null;
  deadline_text: string | null;
  supersedes: string[];
  evidence: Evidence[];
  confidence: number | null;
  flags: string[];
  reasons: Reason[];
  review_state: ReviewState | null;
  scope: "meeting" | "durable" | null;
  timeline: TimelineEntry[];
}

export interface Ledger {
  meeting_id: string;
  generated_by: string;
  threads: { id: string; title: string }[];
  items: Item[];
}

export interface Meeting {
  id: string;
  title: string | null;
  date: string | null;
  participants: Participant[];
  absent: Participant[];
  utterances: Utterance[];
  ledger: Ledger;
  approved: string[];
  published: boolean;
  series_id: string | null;
  questions: Question[];
}

// M3 — một thẻ "Cần bạn trả lời"; codes[k] ↔ texts[k]
export interface Question {
  item_id: string;
  type: ItemType;
  codes: ReasonCode[];
  texts: string[];
}

export type ReviewAction = "confirm" | "reject" | "defer";

export interface KnowledgeEntry {
  series_id: string;
  meeting_id: string;
  item_id: string;
  content: string;
  evidence: Evidence[];
  confirmed_by: string | null;
  confirmed_at: string | null;
}

export interface Series {
  id: string;
  name: string;
  read_only: boolean;
  created_at: string;
  meetings: MeetingSummary[];
  knowledge: KnowledgeEntry[];
  pending: { meeting_id: string; item: Item }[]; // "Việc treo"
}

export interface MeetingSummary {
  id: string;
  title: string | null;
  date: string | null;
  items: number;
  needs_confirmation: number;
  published: boolean;
}
