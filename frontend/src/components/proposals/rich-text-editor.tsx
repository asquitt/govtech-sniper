"use client";

import React, { useCallback, useEffect, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { EditorToolbar } from "./editor-toolbar";
import { AiSuggestion } from "./track-changes-extension";
import { SuggestionToolbar } from "./suggestion-toolbar";

interface RichTextEditorProps {
  content: string;
  onUpdate: (html: string) => void;
  onAutoSave?: (html: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function RichTextEditor({
  content,
  onUpdate,
  onAutoSave,
  disabled = false,
  placeholder = "Write or edit proposal content...",
}: RichTextEditorProps) {
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3, 4] },
      }),
      Placeholder.configure({ placeholder }),
      AiSuggestion,
    ],
    content: wrapPlainText(content),
    editable: !disabled,
    onUpdate: ({ editor: e }) => {
      const html = e.getHTML();
      onUpdate(html);

      // Debounced auto-save
      if (onAutoSave) {
        if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
        autoSaveTimer.current = setTimeout(() => {
          onAutoSave(html);
        }, 1500);
      }
    },
    editorProps: {
      attributes: {
        class:
          "prose prose-sm dark:prose-invert max-w-none px-3 py-2 min-h-[300px] focus:outline-none",
      },
    },
  });

  // Update content when prop changes (e.g., switching sections)
  const prevContentRef = useRef(content);
  useEffect(() => {
    if (editor && content !== prevContentRef.current) {
      prevContentRef.current = content;
      const wrapped = wrapPlainText(content);
      if (editor.getHTML() !== wrapped) {
        editor.commands.setContent(wrapped);
      }
    }
  }, [content, editor]);

  // Update editability
  useEffect(() => {
    if (editor) {
      editor.setEditable(!disabled);
    }
  }, [disabled, editor]);

  // Cleanup auto-save timer
  useEffect(() => {
    return () => {
      if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    };
  }, []);

  return (
    <div className="flex-1 flex flex-col border border-border rounded-md overflow-hidden bg-background">
      <EditorToolbar editor={editor} />
      <SuggestionToolbar editor={editor} />
      <div className="flex-1 overflow-y-auto">
        <EditorContent editor={editor} />
      </div>
      <style>{`
        .ai-suggestion {
          background-color: rgba(250, 204, 21, 0.15);
          border-bottom: 1px dashed rgba(202, 138, 4, 0.5);
          padding: 1px 0;
        }
        .dark .ai-suggestion {
          background-color: rgba(250, 204, 21, 0.1);
          border-bottom-color: rgba(250, 204, 21, 0.3);
        }
      `}</style>
    </div>
  );
}

/**
 * Wrap plain text (no HTML tags) in <p> tags for TipTap.
 * Content that already contains HTML tags is passed through.
 */
function wrapPlainText(text: string): string {
  if (!text) return "";
  // If text contains any HTML tags, assume it's already HTML
  if (/<[a-z][\s\S]*>/i.test(text)) return text;
  // Wrap each line in a <p> tag
  return text
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => `<p>${line}</p>`)
    .join("");
}
