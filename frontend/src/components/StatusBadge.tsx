import type { DocumentStatus } from "../types";
import { Badge } from "./ui";

const STATUS_TONE: Record<DocumentStatus, "neutral" | "accent" | "warning" | "success" | "danger"> = {
  uploaded: "neutral",
  extracting: "accent",
  summarized: "accent",
  pending_review: "warning",
  curated: "success",
  error: "danger",
};

const STATUS_LABEL: Record<DocumentStatus, string> = {
  uploaded: "Uploaded",
  extracting: "Extracting",
  summarized: "Summarized",
  pending_review: "Pending Review",
  curated: "Curated",
  error: "Error",
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>;
}
