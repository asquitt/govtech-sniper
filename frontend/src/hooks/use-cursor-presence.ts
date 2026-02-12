import { useEffect, useRef, useState, useCallback } from "react";
import type { CursorPosition } from "@/types";

const STALE_TIMEOUT = 5_000; // 5s

/**
 * Hook to track cursor positions from other collaborators via WebSocket.
 * Listens for `cursor_update` messages and maintains a Map<userId, CursorPosition>.
 */
export function useCursorPresence(ws: WebSocket | null) {
  const [cursors, setCursors] = useState<Map<number, CursorPosition>>(new Map());
  const cleanupRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Remove stale cursors
  useEffect(() => {
    cleanupRef.current = setInterval(() => {
      setCursors((prev) => {
        const now = Date.now();
        const next = new Map<number, CursorPosition>();
        for (const [uid, pos] of prev) {
          const timestamp = pos.timestamp || pos.updated_at;
          if (!timestamp) {
            continue;
          }
          if (now - new Date(timestamp).getTime() < STALE_TIMEOUT) {
            next.set(uid, pos);
          }
        }
        return next.size === prev.size ? prev : next;
      });
    }, 2_000);

    return () => {
      if (cleanupRef.current) clearInterval(cleanupRef.current);
    };
  }, []);

  // Listen for cursor_update
  useEffect(() => {
    if (!ws) return;

    const handler = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "cursor_update") {
          const data = (msg.data || msg) as CursorPosition;
          if (typeof data.user_id !== "number") {
            return;
          }
          setCursors((prev) => {
            const next = new Map(prev);
            next.set(data.user_id, data);
            return next;
          });
        }
      } catch {
        // ignore non-JSON or malformed
      }
    };

    ws.addEventListener("message", handler);
    return () => ws.removeEventListener("message", handler);
  }, [ws]);

  /** Send own cursor position. */
  const sendCursor = useCallback(
    (sectionId: number, position: number) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: "cursor_update",
            data: { section_id: sectionId, position },
          })
        );
      }
    },
    [ws]
  );

  return { cursors, sendCursor };
}
