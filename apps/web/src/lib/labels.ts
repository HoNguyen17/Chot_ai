import type { ItemType, Status } from "./types";

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

/** Nhóm "Kết quả — tự chấp nhận" (thứ tự hiển thị). Nhãn trạng thái thì lấy item.status_label từ API. */
export const RESULT_GROUPS: { key: string; title: string; types: ItemType[] }[] = [
  { key: "decision", title: "Quyết định", types: ["decision"] },
  { key: "task", title: "Công việc", types: ["task"] },
  { key: "blocker", title: "Vướng mắc", types: ["blocker"] },
  { key: "open_question", title: "Câu hỏi mở", types: ["open_question"] },
  { key: "knowledge", title: "Tri thức", types: ["knowledge"] },
  { key: "other", title: "Yêu cầu & phản hồi", types: ["request", "feedback"] },
  { key: "history", title: "Lịch sử phương án", types: ["option"] },
];

/** Mục bị thay thế / bị bác dồn về "Lịch sử" dù thuộc type nào. */
export function groupKey(type: ItemType, status: Status): string {
  if (status === "superseded" || status === "rejected") return "history";
  return RESULT_GROUPS.find((g) => g.types.includes(type))?.key ?? "other";
}

/** Động từ cho từng bước "Vì sao" (timeline sự kiện quyết định). */
export const EVENT_VERB: Record<string, string> = {
  propose: "đề xuất",
  revise: "đổi đề xuất",
  object: "phản đối",
  agree: "đồng ý",
  defer: "hoãn",
  reopen: "lật lại",
};
