"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { IngestedEmail } from "@/types/email-ingest";

interface EmailHistoryTableProps {
  history: IngestedEmail[];
  historyTotal: number;
  onReprocess: (emailId: number) => void;
}

function statusVariant(
  status: IngestedEmail["processing_status"]
): "default" | "success" | "destructive" | "outline" {
  switch (status) {
    case "processed":
      return "success";
    case "error":
      return "destructive";
    case "ignored":
      return "outline";
    default:
      return "default";
  }
}

export function EmailHistoryTable({
  history,
  historyTotal,
  onReprocess,
}: EmailHistoryTableProps) {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-foreground">
        Ingested Emails ({historyTotal})
      </h2>

      {history.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No emails ingested yet.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="py-2 pr-4">Subject</th>
                <th className="py-2 pr-4">Sender</th>
                <th className="py-2 pr-4">Received</th>
                <th className="py-2 pr-4">Attachments</th>
                <th className="py-2 pr-4">Confidence</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Opportunity</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-border last:border-0"
                >
                  <td className="py-2 pr-4 max-w-[250px] truncate">
                    {item.subject}
                  </td>
                  <td className="py-2 pr-4">{item.sender}</td>
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {new Date(item.received_at).toLocaleDateString()}
                  </td>
                  <td className="py-2 pr-4">
                    {item.attachment_count > 0
                      ? `${item.attachment_count} (${item.attachment_names.slice(0, 2).join(", ")})`
                      : "0"}
                  </td>
                  <td className="py-2 pr-4">
                    {item.classification_confidence !== null
                      ? item.classification_confidence.toFixed(2)
                      : "\u2014"}
                  </td>
                  <td className="py-2 pr-4">
                    <Badge variant={statusVariant(item.processing_status)}>
                      {item.processing_status}
                    </Badge>
                  </td>
                  <td className="py-2 pr-4">
                    {item.created_rfp_id ? (
                      <a
                        className="text-primary underline"
                        href={`/opportunities/${item.created_rfp_id}`}
                      >
                        #{item.created_rfp_id}
                      </a>
                    ) : (
                      "\u2014"
                    )}
                  </td>
                  <td className="py-2">
                    {(item.processing_status === "error" ||
                      item.processing_status === "ignored") && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onReprocess(item.id)}
                      >
                        Reprocess
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
