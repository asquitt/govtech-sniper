import { Mark, mergeAttributes, type Editor } from "@tiptap/core";

export interface AiSuggestionOptions {
  HTMLAttributes: Record<string, string>;
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    aiSuggestion: {
      /** Apply the AI suggestion mark to the current selection */
      setAiSuggestion: (attrs?: {
        author?: string;
        timestamp?: string;
        suggestionId?: string;
      }) => ReturnType;
      /** Remove the AI suggestion mark from the current selection */
      unsetAiSuggestion: () => ReturnType;
      /** Accept suggestion: remove mark but keep content */
      acceptSuggestion: () => ReturnType;
      /** Reject suggestion: remove both mark and content */
      rejectSuggestion: () => ReturnType;
      /** Accept all AI suggestions in the document */
      acceptAllSuggestions: () => ReturnType;
      /** Reject all AI suggestions in the document */
      rejectAllSuggestions: () => ReturnType;
    };
  }
}

export const AiSuggestion = Mark.create<AiSuggestionOptions>({
  name: "aiSuggestion",

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      author: {
        default: "AI",
        parseHTML: (el) => el.getAttribute("data-author") ?? "AI",
        renderHTML: (attrs) => ({ "data-author": attrs.author }),
      },
      timestamp: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-timestamp"),
        renderHTML: (attrs) =>
          attrs.timestamp ? { "data-timestamp": attrs.timestamp } : {},
      },
      suggestionId: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-suggestion-id"),
        renderHTML: (attrs) =>
          attrs.suggestionId
            ? { "data-suggestion-id": attrs.suggestionId }
            : {},
      },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-ai-suggestion="true"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "span",
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, {
        "data-ai-suggestion": "true",
        class: "ai-suggestion",
      }),
      0,
    ];
  },

  addCommands() {
    return {
      setAiSuggestion:
        (attrs) =>
        ({ commands }) =>
          commands.setMark(this.name, attrs),

      unsetAiSuggestion:
        () =>
        ({ commands }) =>
          commands.unsetMark(this.name),

      acceptSuggestion:
        () =>
        ({ commands }) =>
          commands.unsetMark(this.name),

      rejectSuggestion:
        () =>
        ({ state, tr, dispatch }) => {
          const { from, to } = state.selection;
          const markType = state.schema.marks[this.name];
          if (!markType) return false;

          // Check if selection has the AI suggestion mark
          let hasMark = false;
          state.doc.nodesBetween(from, to, (node) => {
            if (markType.isInSet(node.marks)) {
              hasMark = true;
            }
          });

          if (!hasMark) return false;

          if (dispatch) {
            tr.deleteRange(from, to);
            dispatch(tr);
          }
          return true;
        },

      acceptAllSuggestions:
        () =>
        ({ state, tr, dispatch }) => {
          const markType = state.schema.marks[this.name];
          if (!markType) return false;

          if (dispatch) {
            tr.removeMark(0, state.doc.content.size, markType);
            dispatch(tr);
          }
          return true;
        },

      rejectAllSuggestions:
        () =>
        ({ state, tr, dispatch }) => {
          const markType = state.schema.marks[this.name];
          if (!markType) return false;

          if (dispatch) {
            // Collect ranges in reverse order so deletions don't shift positions
            const ranges: { from: number; to: number }[] = [];

            state.doc.descendants((node, pos) => {
              if (markType.isInSet(node.marks)) {
                const end = pos + node.nodeSize;
                // Merge with previous range if adjacent
                const last = ranges[ranges.length - 1];
                if (last && last.to === pos) {
                  last.to = end;
                } else {
                  ranges.push({ from: pos, to: end });
                }
              }
            });

            // Delete in reverse to preserve positions
            for (let i = ranges.length - 1; i >= 0; i--) {
              tr.delete(ranges[i].from, ranges[i].to);
            }
            dispatch(tr);
          }
          return true;
        },
    };
  },
});

/**
 * Count the number of text nodes with the aiSuggestion mark in the document.
 * Returns the count of distinct marked ranges.
 */
export function countAiSuggestions(editor: Editor): number {
  let count = 0;
  let inSuggestion = false;

  editor.state.doc.descendants((node) => {
    const hasMark = node.marks.some((m) => m.type.name === "aiSuggestion");
    if (hasMark && !inSuggestion) {
      count++;
      inSuggestion = true;
    } else if (!hasMark) {
      inSuggestion = false;
    }
  });

  return count;
}

/**
 * Wrap HTML content in AI suggestion marks by adding data attributes.
 * Used when inserting AI-generated content into the editor.
 */
export function wrapInSuggestionMarks(
  html: string,
  author: string = "AI",
): string {
  const id = crypto.randomUUID();
  const ts = new Date().toISOString();
  return `<span data-ai-suggestion="true" data-author="${author}" data-timestamp="${ts}" data-suggestion-id="${id}" class="ai-suggestion">${html}</span>`;
}
