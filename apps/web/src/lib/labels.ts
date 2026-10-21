import type { ItemType, Status } from "./types";

export const STATUS_LABEL: Record<Status, string> = {
  final: "Đã chốt",
  needs_confirmation: "Cần xác nhận",
  superseded: "Bị thay thế",
  rejected: "Bị bác",
  deferred: "Hoãn",
  open: "Đang mở",
  noted: "Ghi nhận",
};

export const TYPE_LABEL: Record<ItemType, string> = {
  decision: "Quyết định",
  option: "Phương án",
  task: "Công việc",
  blocker: "Vướng mắc",
  open_question: "Câu hỏi mở",
  knowledge: "Tri thức",
  request: "Yêu cầu",
  feedback: "Phản hồi",
};

/** Thứ tự các nhóm trên màn hình duyệt: việc cần người xử lý đứng đầu. */
export const SECTIONS: { key: string; title: string; hint: string; match: (t: ItemType, s: Status) => boolean }[] = [
  {
    key: "confirm",
    title: "Cần bạn xác nhận",
    hint: "AI không đủ bằng chứng để tự chốt. Duyệt từng mục trước khi xuất bản.",
    match: (_t, s) => s === "needs_confirmation",
  },
  {
    key: "decisions",
    title: "Đã chốt",
    hint: "Cam kết rõ của người chủ trì, không bị lật lại sau đó.",
    match: (t, s) => t === "decision" && s === "final",
  },
  {
    key: "tasks",
    title: "Công việc đã nhận",
    hint: "Có người nhận rõ ràng.",
    match: (t, s) => t === "task" && s === "open",
  },
  {
    key: "pending",
    title: "Hoãn & còn bỏ ngỏ",
    hint: "Sẽ được đưa vào buổi họp sau.",
    match: (t, s) => s === "deferred" || ((t === "open_question" || t === "blocker" || t === "option") && s === "open"),
  },
  {
    key: "notes",
    title: "Ghi nhận khác",
    hint: "Tri thức, yêu cầu, phản hồi.",
    match: (t, s) => (t === "knowledge" || t === "request" || t === "feedback") && (s === "open" || s === "noted"),
  },
  {
    key: "history",
    title: "Lịch sử: phương án bị thay thế",
    hint: "Giữ lại để biết cuộc họp đã đi đường vòng thế nào.",
    match: (_t, s) => s === "superseded" || s === "rejected",
  },
];
