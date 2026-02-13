"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background font-sans">
        <div className="flex min-h-screen items-center justify-center p-8">
          <div className="text-center max-w-md">
            <h2 className="text-xl font-semibold text-red-500 mb-2">
              Critical Error
            </h2>
            <p className="text-sm text-gray-400 mb-6">
              {error.message || "Something went critically wrong."}
            </p>
            <button
              onClick={reset}
              className="rounded-md bg-white px-4 py-2 text-sm font-medium text-black hover:bg-gray-200 transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
