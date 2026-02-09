import { OfficeScriptLoader } from "./_components/office-script-loader";

export const metadata = {
  title: "RFP Sniper | Word Add-in",
  description: "AI-powered proposal editing inside Microsoft Word",
};

export default function WordAddinLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/* Load Office.js only in likely Office host environments */}
      <OfficeScriptLoader />
      <div className="min-h-screen bg-background text-foreground">
        {/* Compact header for task pane (300-350px wide) */}
        <header className="flex items-center gap-2 px-3 py-2 border-b border-border bg-card">
          <div className="w-5 h-5 rounded bg-primary flex items-center justify-center">
            <span className="text-[10px] font-bold text-primary-foreground">R</span>
          </div>
          <span className="text-sm font-semibold">RFP Sniper</span>
        </header>
        <main className="p-3">{children}</main>
      </div>
    </>
  );
}
