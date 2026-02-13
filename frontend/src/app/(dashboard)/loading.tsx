export default function DashboardLoading() {
  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex-1 p-6 space-y-6">
        <div className="h-8 w-48 rounded-md bg-muted animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-28 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
        <div className="h-64 rounded-lg bg-muted animate-pulse" />
        <div className="h-40 rounded-lg bg-muted animate-pulse" />
      </div>
    </div>
  );
}
