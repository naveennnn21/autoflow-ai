"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SeriesPoint } from "@/types";

const AreaChart = dynamic(() => import("./area-chart"), { ssr: false });

function formatDay(date: string): string {
  const d = new Date(`${date}T00:00:00`);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function OverviewChart({ series }: { series: SeriesPoint[] }) {
  const data = series.map((s) => ({
    day: formatDay(s.date),
    runs: s.runs,
    success: s.success,
  }));

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>Executions</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">Last {series.length || 30} days</Badge>
        </div>
      </CardHeader>
      <CardContent className="h-72">
        <AreaChart data={data} />
      </CardContent>
    </Card>
  );
}
