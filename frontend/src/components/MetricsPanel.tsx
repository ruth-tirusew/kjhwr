import type { Buffer, Coverage, ErrorMetrics, MetricsResponse } from "@/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Cell, Head, Row, Table } from "@/components/ui/table";
import { fmtMinute, mw, signedMw } from "@/lib/format";

export function CoverageNote({ c, unit }: { c: Coverage; unit: string }) {
  return (
    <p className="text-muted-foreground text-xs">
      Scored <span className="text-foreground font-mono">{c.scored}</span> of{" "}
      <span className="text-foreground font-mono">{c.targets}</span> half-hours in {unit}.
      {c.off_forecast_grid > 0 &&
        ` WINDFOR is published hourly, so the ${c.off_forecast_grid} half-hour targets between forecasts are not scored.`}
      {c.no_forecast > 0 && ` ${c.no_forecast} on-the-hour targets had no forecast published by the cutoff.`}
      {c.no_actual > 0 && ` ${c.no_actual} had no actual.`} Nothing is filled in.
    </p>
  );
}

export function DayStats({ metrics: m }: { metrics: ErrorMetrics }) {
  return (
    <dl className="grid grid-cols-3 border text-sm">
      {(
        [
          ["Day MAE", mw(m.mae)],
          ["Day bias (forecast − actual)", signedMw(m.bias)],
          ["Half-hours scored", String(m.n)],
        ] as const
      ).map(([k, v]) => (
        <div key={k} className="border-r px-3 py-2 last:border-r-0">
          <dt className="text-muted-foreground text-xs">{k}</dt>
          <dd className="font-mono tabular-nums">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

type BufferProps = { buffer: Buffer; coverage: Coverage; adjustmentMw?: number | null } & (
  { basis: "trailing"; windowStart: string; knownUntil: string } | { basis: "retrospective" }
);

export function BufferCard(props: BufferProps) {
  const { buffer, coverage, adjustmentMw } = props;
  const pct = Math.round(buffer.quantile * 100);
  const subtitle =
    props.basis === "trailing"
      ? `P${pct} · errors known at the cutoff (${props.windowStart.slice(0, 10)} to ${fmtMinute(props.knownUntil)})`
      : `P${pct} · January 2026 retrospective, includes days after the delivery day`;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Procurement buffer</CardTitle>
        <CardDescription>{subtitle}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {buffer.buffer_mw === null ? (
          <p className="text-muted-foreground text-sm">No earlier errors to learn from yet for this day.</p>
        ) : (
          <>
            <p className="font-mono text-4xl font-semibold tabular-nums">{mw(buffer.buffer_mw)}</p>
            <p className="text-sm">
              Across the {buffer.n} scored half-hours in this window, actual wind fell short of the forecast by no more
              than this in {pct}% of them (half-hours with no shortfall count as zero). Wind under-delivered in{" "}
              {buffer.n_shortfall} of {buffer.n}. Treat the tail with caution given the sample size.
            </p>
            {adjustmentMw != null && (
              <p className="text-sm">
                Bias-adjusted: every forecast had {mw(adjustmentMw)} removed, the average over-forecast known at the
                cutoff, before this buffer was computed. It covers what is left after that correction.
              </p>
            )}
          </>
        )}
        <CoverageNote c={coverage} unit="this window" />
      </CardContent>
    </Card>
  );
}

export function AccuracyCard({ data }: { data: MetricsResponse }) {
  const m = data.metrics;
  const rows: [string, string][] = [
    ["MAE", mw(m.mae)],
    ["RMSE", mw(m.rmse)],
    ["Bias (forecast − actual)", signedMw(m.bias)],
    ["P50 absolute error", mw(m.p50_abs)],
    ["P90 absolute error", mw(m.p90_abs)],
    ["P95 absolute error", mw(m.p95_abs)],
    ["Half-hours compared", String(m.n)],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Forecast accuracy</CardTitle>
        <CardDescription>January 2026, retrospective</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <tbody>
            {rows.map(([k, v]) => (
              <Row key={k}>
                <Head>{k}</Head>
                <Cell>{v}</Cell>
              </Row>
            ))}
          </tbody>
        </Table>
      </CardContent>
    </Card>
  );
}
