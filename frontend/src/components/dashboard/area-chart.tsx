"use client";

import {
  Area,
  AreaChart as ReAreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const data = [
  { day: "Jan", runs: 2400, success: 2350 },
  { day: "Feb", runs: 3800, success: 3720 },
  { day: "Mar", runs: 5200, success: 5100 },
  { day: "Apr", runs: 6900, success: 6800 },
  { day: "May", runs: 8100, success: 7950 },
  { day: "Jun", runs: 9800, success: 9660 },
  { day: "Jul", runs: 12400, success: 12240 },
];

export default function AreaChart() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ReAreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <defs>
          <linearGradient id="runs" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.5} />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="success" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--success))" stopOpacity={0.4} />
            <stop offset="100%" stopColor="hsl(var(--success))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
        <XAxis dataKey="day" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{
            background: "hsl(var(--popover))",
            border: "1px solid hsl(var(--border))",
            borderRadius: 12,
            fontSize: 12,
          }}
        />
        <Area type="monotone" dataKey="runs" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#runs)" />
        <Area type="monotone" dataKey="success" stroke="hsl(var(--success))" strokeWidth={2} fill="url(#success)" />
      </ReAreaChart>
    </ResponsiveContainer>
  );
}
