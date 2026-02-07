/**
 * Ambient type declarations for Office.js loaded from CDN.
 * These provide basic type safety without pulling in the full @types/office-js package.
 */

interface OfficeInfo {
  host: string | null;
  platform: string | null;
}

interface OfficeReadyResult {
  host: string;
  platform: string;
}

declare namespace Office {
  function onReady(callback?: (info: OfficeReadyResult) => void): Promise<OfficeReadyResult>;
  const context: { host: string | null };
  enum HostType {
    Word = "Word",
    Excel = "Excel",
    PowerPoint = "PowerPoint",
    Outlook = "Outlook",
  }
}

declare namespace Word {
  function run<T>(callback: (context: RequestContext) => Promise<T>): Promise<T>;

  enum InsertLocation {
    before = "Before",
    after = "After",
    start = "Start",
    end = "End",
    replace = "Replace",
  }

  interface RequestContext {
    document: Document;
    sync(): Promise<void>;
  }

  interface Document {
    body: Body;
    getSelection(): Range;
  }

  interface Body {
    insertHtml(html: string, insertLocation: InsertLocation | string): Range;
    insertParagraph(text: string, insertLocation: InsertLocation | string): Paragraph;
    search(searchText: string, searchOptions?: { matchCase?: boolean }): RangeCollection;
    paragraphs: ParagraphCollection;
    getOoxml(): any;
    load(properties: string): void;
    text: string;
  }

  interface Range {
    insertText(text: string, insertLocation: InsertLocation | string): Range;
    insertHtml(html: string, insertLocation: InsertLocation | string): Range;
    font: Font;
    text: string;
    load(properties: string): void;
  }

  interface RangeCollection {
    items: Range[];
    load(properties: string): void;
  }

  interface Font {
    highlightColor: string;
    bold: boolean;
    italic: boolean;
  }

  interface Paragraph {
    style: string;
    font: Font;
    load(properties: string): void;
  }

  interface ParagraphCollection {
    items: Paragraph[];
    getLast(): Paragraph;
    load(properties: string): void;
  }
}
