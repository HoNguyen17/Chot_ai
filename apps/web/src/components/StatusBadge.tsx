import { STATUS_LABEL } from "@/lib/labels";
import type { Status } from "@/lib/types";

/** Trạng thái luôn có CHỮ, không chỉ dựa vào màu (accessibility). */
export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABEL[status]}</span>;
}
