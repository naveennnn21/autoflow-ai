"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const AreaChart = dynamic(() => import("./area-chart"), { ssr: false });

export function OverviewChart() {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>Executions</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">Last 30 days</Badge>
        </div>
      </CardHeader>
      <CardContent className="h-72">
        <AreaChart />
      </CardContent>
    </Card>
  );
}
