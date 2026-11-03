import { defineChart, lineY } from "@tanstack/charts";
import { scaleLinear } from "@tanstack/charts/scales/linear";
import { Chart } from "@tanstack/charts/react";
import { tooltip } from "@tanstack/charts/tooltip";
import { scaleUtc } from "d3-scale";
import { useMemo } from "react";
import type { ForecastRow } from "@/api";

export const FORECAST_COLOR = "#2563eb";
export const ACTUAL_COLOR = "#ea580c";
export const ADJUSTED_COLOR = "#16a34a";

type Point = { time: Date; mw: number | null };

export function ForecastChart({ rows, showAdjusted }: { rows: ForecastRow[]; showAdjusted: boolean }) {
  const definition = useMemo(() => {
    // Missing values stay missing: null rows break the line instead of being filled.
    const forecast: Point[] = rows.map((r) => ({ time: new Date(r.target_time), mw: r.forecast_mw }));
    const actual: Point[] = rows.map((r) => ({ time: new Date(r.target_time), mw: r.actual_mw }));
    const adjusted: Point[] = rows.map((r) => ({ time: new Date(r.target_time), mw: r.adjusted_mw }));
    // Anchor at zero so the gap between the lines is not visually exaggerated.
    const peak = Math.max(0, ...rows.flatMap((r) => [r.forecast_mw ?? 0, r.actual_mw ?? 0]));
    const top = Math.ceil(peak / 2000) * 2000 || 2000;
    return defineChart({
      marks: [
        lineY(forecast, { id: "forecast", x: "time", y: "mw", stroke: FORECAST_COLOR, points: true }),
        lineY(actual, { id: "actual", x: "time", y: "mw", stroke: ACTUAL_COLOR }),
        ...(showAdjusted
          ? [lineY(adjusted, { id: "adjusted", x: "time", y: "mw", stroke: ADJUSTED_COLOR, points: true })]
          : []),
      ],
      scales: {
        x: {
          scale: scaleUtc,
          axis: { label: "Time (UTC, 24h)", ticks: { format: (v) => new Date(v as Date).toISOString().slice(11, 16) } },
        },
        y: { scale: scaleLinear().domain([0, top]), grid: true, axis: { label: "Wind generation (MW)" } },
      },
      tooltip,
    });
  }, [rows, showAdjusted]);

  return <Chart definition={definition} height={420} ariaLabel="Forecast versus actual wind generation" />;
}
