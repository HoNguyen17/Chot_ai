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
  | "open";

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
  utt: string;
  quote: string;
  ts: string | null;
  speaker: string | null;
}

export interface Item {
  id: string;
  type: ItemType;
  thread: string | null;
  content: string;
  status: Status;
  owner: string | null;
  decided_by: string | null;
  deadline: string | null;
  deadline_text: string | null;
  supersedes: string[];
  evidence: Evidence[];
  confidence: number | null;
  flags: string[];
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
}

export interface MeetingSummary {
  id: string;
  title: string | null;
  date: string | null;
  items: number;
  needs_confirmation: number;
  published: boolean;
}
