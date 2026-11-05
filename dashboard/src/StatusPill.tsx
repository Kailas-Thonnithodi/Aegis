import type { Status } from "./api";
import { statusLabels } from "./format";

export function StatusPill({ status }: Readonly<{ status: Status }>) {
  return <span className={`pill pill-${status}`}>{statusLabels[status]}</span>;
}
