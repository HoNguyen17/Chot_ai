import type { Item } from "@/lib/types";

/** Trạng thái luôn có CHỮ, không chỉ dựa vào màu (accessibility). Chữ theo type, lấy từ API. */
export function StatusBadge({ item }: { item: Pick<Item, "status" | "status_label"> }) {
  return <span className={`badge badge-${item.status}`}>{item.status_label}</span>;
}
