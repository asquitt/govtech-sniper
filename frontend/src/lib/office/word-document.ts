/**
 * Word document manipulation utilities via Office.js.
 * All functions require Office.js to be loaded and running inside Word.
 */

export class OfficeNotAvailableError extends Error {
  constructor() {
    super(
      "Office.js is not available. Open this page inside Microsoft Word."
    );
    this.name = "OfficeNotAvailableError";
  }
}

function ensureOffice(): void {
  if (typeof Word === "undefined" || !Word.run) {
    throw new OfficeNotAvailableError();
  }
}

/**
 * Insert a proposal section into the Word document.
 * Adds a heading followed by the HTML content.
 */
export async function insertSectionContent(
  title: string,
  htmlContent: string
): Promise<void> {
  ensureOffice();
  await Word.run(async (context) => {
    const body = context.document.body;

    // Insert section heading
    const heading = body.insertParagraph(title, "End");
    heading.style = "Heading 2";

    // Insert HTML content after the heading
    if (htmlContent.trim()) {
      body.insertHtml(htmlContent, "End");
    }

    // Add a separator paragraph
    body.insertParagraph("", "End");

    await context.sync();
  });
}

/**
 * Get the currently selected text in the Word document.
 */
export async function getSelectedText(): Promise<string> {
  ensureOffice();
  return Word.run(async (context) => {
    const selection = context.document.getSelection();
    selection.load("text");
    await context.sync();
    return selection.text;
  });
}

/**
 * Replace the current selection with new text.
 */
export async function replaceSelection(newText: string): Promise<void> {
  ensureOffice();
  await Word.run(async (context) => {
    const selection = context.document.getSelection();
    selection.insertText(newText, "Replace");
    await context.sync();
  });
}

/**
 * Replace the current selection with HTML content.
 */
export async function replaceSelectionHtml(html: string): Promise<void> {
  ensureOffice();
  await Word.run(async (context) => {
    const selection = context.document.getSelection();
    selection.insertHtml(html, "Replace");
    await context.sync();
  });
}

/**
 * Insert text at the current cursor position.
 */
export async function insertAtCursor(text: string): Promise<void> {
  ensureOffice();
  await Word.run(async (context) => {
    const selection = context.document.getSelection();
    selection.insertText(text, "After");
    await context.sync();
  });
}

/**
 * Get the full document body text.
 */
export async function getDocumentBodyText(): Promise<string> {
  ensureOffice();
  return Word.run(async (context) => {
    const body = context.document.body;
    body.load("text");
    await context.sync();
    return body.text;
  });
}

/**
 * Search for text in the document and highlight it.
 * Returns the number of matches found.
 */
export async function highlightText(
  searchText: string,
  color: string = "Yellow"
): Promise<number> {
  ensureOffice();
  return Word.run(async (context) => {
    const results = context.document.body.search(searchText, {
      matchCase: false,
    });
    results.load("font");
    await context.sync();

    for (let i = 0; i < results.items.length; i++) {
      results.items[i].font.highlightColor = color;
    }
    await context.sync();

    return results.items.length;
  });
}

/**
 * Clear all highlights from the document body.
 */
export async function clearHighlights(): Promise<void> {
  ensureOffice();
  await Word.run(async (context) => {
    const body = context.document.body;
    const paragraphs = body.paragraphs;
    paragraphs.load("font");
    await context.sync();

    for (let i = 0; i < paragraphs.items.length; i++) {
      paragraphs.items[i].font.highlightColor = "None";
    }
    await context.sync();
  });
}
