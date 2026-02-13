import {
  Target,
  Clock,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface OpportunityStats {
  total: number;
  qualified: number;
  pending: number;
  analyzing: number;
}

export function StatsCards({ stats }: { stats: OpportunityStats }) {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total RFPs</p>
              <p className="text-2xl font-bold text-primary">{stats.total}</p>
            </div>
            <Target className="w-8 h-8 text-primary/50" />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-accent/5 to-accent/10 border-accent/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Qualified</p>
              <p className="text-2xl font-bold text-accent">
                {stats.qualified}
              </p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-accent/50" />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-warning/5 to-warning/10 border-warning/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Pending Filter</p>
              <p className="text-2xl font-bold text-warning">
                {stats.pending}
              </p>
            </div>
            <Clock className="w-8 h-8 text-warning/50" />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-secondary/50 to-secondary border-border">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Analyzing</p>
              <p className="text-2xl font-bold">{stats.analyzing}</p>
            </div>
            {stats.analyzing > 0 ? (
              <Loader2 className="w-8 h-8 text-muted-foreground/50 animate-spin" />
            ) : (
              <Loader2 className="w-8 h-8 text-muted-foreground/50" />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
