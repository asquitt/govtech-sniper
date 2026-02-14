import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { SectionEditor } from "@/app/(dashboard)/proposals/[proposalId]/_components/section-editor";
import { draftApi } from "@/lib/api";

vi.mock("@/components/proposals/rich-text-editor", () => ({
  RichTextEditor: ({
    content,
    onUpdate,
  }: {
    content: string;
    onUpdate: (value: string) => void;
  }) => (
    <textarea
      aria-label="Mock rich text editor"
      value={content}
      onChange={(event) => onUpdate(event.target.value)}
    />
  ),
}));

vi.mock("@/components/proposals/writing-plan-panel", () => ({
  WritingPlanPanel: () => <div>Writing Plan Panel</div>,
}));

vi.mock("@/lib/api", () => ({
  draftApi: {
    rewriteSection: vi.fn(),
    expandSection: vi.fn(),
  },
}));

const mockedDraftApi = vi.mocked(draftApi);

describe("SectionEditor track changes", () => {
  it("wraps rewrite output in AI suggestion marks", async () => {
    const handleContentChange = vi.fn();
    mockedDraftApi.rewriteSection.mockResolvedValue({
      id: 1,
      proposal_id: 1,
      title: "Technical Approach",
      section_number: "1.0",
      status: "editing",
      display_order: 1,
      created_at: "2026-02-14T00:00:00Z",
      updated_at: "2026-02-14T00:00:00Z",
      generated_content: {
        raw_text: "Rewritten proposal text",
        clean_text: "Rewritten proposal text",
        citations: [],
        model_used: "mock",
        tokens_used: 30,
        generation_time_seconds: 0.3,
      },
      final_content: "Original text",
      assigned_to_user_id: null,
      assigned_at: null,
    });

    render(
      <SectionEditor
        selectedSection={{
          id: 1,
          proposal_id: 1,
          title: "Technical Approach",
          section_number: "1.0",
          status: "editing",
          display_order: 1,
          created_at: "2026-02-14T00:00:00Z",
          updated_at: "2026-02-14T00:00:00Z",
          final_content: "Original text",
          assigned_to_user_id: null,
          assigned_at: null,
        }}
        editorContent="Original text"
        onEditorContentChange={handleContentChange}
        writingPlan=""
        onWritingPlanChange={() => {}}
        onSaveWritingPlan={() => {}}
        isSavingPlan={false}
        onSave={() => {}}
        onApprove={() => {}}
        isSaving={false}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Rewrite" }));
    fireEvent.click(screen.getByRole("button", { name: "professional" }));

    await waitFor(() =>
      expect(mockedDraftApi.rewriteSection).toHaveBeenCalledWith(1, { tone: "professional" })
    );
    await waitFor(() => expect(handleContentChange).toHaveBeenCalled());

    const latestContent = handleContentChange.mock.calls.at(-1)?.[0] as string;
    expect(latestContent).toContain('data-ai-suggestion="true"');
    expect(latestContent).toContain("Rewritten proposal text");
  });
});
