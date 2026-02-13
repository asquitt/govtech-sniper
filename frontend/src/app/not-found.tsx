import Link from "next/link";

export default function RootNotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="rounded-lg border border-border bg-card p-8 text-center max-w-md">
        <h2 className="text-4xl font-bold text-foreground mb-2">404</h2>
        <p className="text-sm text-muted-foreground mb-6">
          Page not found. The page you&apos;re looking for doesn&apos;t exist.
        </p>
        <Link
          href="/"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Go home
        </Link>
      </div>
    </div>
  );
}
