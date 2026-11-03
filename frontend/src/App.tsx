import { useState } from "react";
import { ACTUAL_COLOR, ADJUSTED_COLOR, FORECAST_COLOR, ForecastChart } from "@/components/ForecastChart";
import { AccuracyCard, BufferCard, CoverageNote, DayStats } from "@/components/MetricsPanel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/field";
import { fmtMinute, fmtSeconds, hoursBetween } from "@/lib/format";
import { useForecast, useMetrics, useTrailingBuffer } from "@/queries";

const START = "2026-01-01";
const END = "2026-01-31";
const DAYS = Array.from({ length: 31 }, (_, i) => `2026-01-${String(i + 1).padStart(2, "0")}`);
const CUTOFF_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

function Swatch({ color, dot, children }: { color: string; dot?: boolean; children: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={dot ? "inline-block size-2 rounded-full" : "inline-block h-0.5 w-4"}
        style={{ background: color }}
      />
      {children}
    </span>
  );
}

export default function App() {
  const [day, setDay] = useState("2026-01-15");
  const [cutoffDraft, setCutoffDraft] = useState("09:00");
  const [cutoffTime, setCutoffTime] = useState("09:00");
  const [quantile, setQuantile] = useState(0.9);
  const [basis, setBasis] = useState<"trailing" | "retrospective">("trailing");
  const [adjusted, setAdjusted] = useState(false);

  const forecast = useForecast(day, cutoffTime);
  const metrics = useMetrics(START, END, cutoffTime, quantile);
  const trailing = useTrailingBuffer(day, cutoffTime, quantile, adjusted);

  const rows = forecast.data?.rows ?? [];
  const published = rows
    .map((r) => r.publish_time)
    .filter((t): t is string => !!t)
    .sort();
  const firstPub = published[0];
  const lastPub = published[published.length - 1];
  const firstTarget = rows[0]?.target_time;
  const snap = forecast.data ?? metrics.data;
  const error = forecast.error ?? metrics.error ?? trailing.error;

  return (
    <main className="mx-auto max-w-6xl space-y-4 px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-2 border-b pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Wind Forecast Decision Portal</h1>
          <p className="text-muted-foreground text-sm">Day-ahead national wind forecast, as known at your cutoff</p>
        </div>
        {snap && (
          <p className="text-muted-foreground border px-2 py-1 font-mono text-xs">
            snapshot {snap.snapshot_id} · fetched {fmtSeconds(snap.fetched_at)}
          </p>
        )}
      </header>

      <Card>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Label>
            Delivery day
            <Select value={day} onChange={(e) => setDay(e.target.value)}>
              {DAYS.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </Select>
          </Label>
          <Label>
            Cutoff on the day before (UK, HH:MM)
            <Input
              value={cutoffDraft}
              inputMode="numeric"
              placeholder="09:00"
              aria-invalid={!CUTOFF_RE.test(cutoffDraft)}
              onChange={(e) => {
                setCutoffDraft(e.target.value);
                if (CUTOFF_RE.test(e.target.value)) setCutoffTime(e.target.value);
              }}
            />
          </Label>
          <Label>
            Buffer confidence
            <Select value={quantile} onChange={(e) => setQuantile(Number(e.target.value))}>
              <option value={0.9}>P90</option>
              <option value={0.95}>P95</option>
            </Select>
          </Label>
          <Label>
            Buffer based on
            <Select value={basis} onChange={(e) => setBasis(e.target.value as typeof basis)}>
              <option value="trailing">Errors known at the cutoff</option>
              <option value="retrospective">All of January (retrospective)</option>
            </Select>
          </Label>
          <Label>
            Forecast view
            <Select value={adjusted ? "adjusted" : "raw"} onChange={(e) => setAdjusted(e.target.value === "adjusted")}>
              <option value="raw">Raw forecast</option>
              <option value="adjusted">Bias-adjusted</option>
            </Select>
          </Label>
        </CardContent>
      </Card>

      {error && (
        <p role="alert" className="border-destructive text-destructive border px-3 py-2 text-sm">
          {String(error)}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Forecast known at cutoff vs actual</CardTitle>
            <CardDescription>Delivery day {day}, times in UTC</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {forecast.isPending ? (
              <p className="text-muted-foreground text-sm">Loading…</p>
            ) : forecast.data ? (
              <>
                <DayStats metrics={adjusted ? forecast.data.adjusted_metrics : forecast.data.metrics} />
                <p className="flex flex-wrap gap-4 text-xs">
                  <Swatch color={FORECAST_COLOR} dot>
                    Forecast (hourly)
                  </Swatch>
                  <Swatch color={ACTUAL_COLOR}>Actual (half-hourly)</Swatch>
                  {adjusted && (
                    <Swatch color={ADJUSTED_COLOR} dot>
                      Bias-adjusted forecast
                    </Swatch>
                  )}
                </p>
                <ForecastChart rows={rows} showAdjusted={adjusted} />
                <CoverageNote c={forecast.data.coverage} unit="this day" />
                <p className="text-muted-foreground text-xs">
                  Cutoff {fmtMinute(forecast.data.cutoff)}.{" "}
                  {firstPub && lastPub && firstTarget
                    ? `Forecasts used were published ${fmtMinute(firstPub)}${lastPub !== firstPub ? ` to ${fmtMinute(lastPub)}` : ""}. The newest is ${hoursBetween(lastPub, forecast.data.cutoff)} h old at the cutoff and was published ${hoursBetween(lastPub, firstTarget)} h before the first target.`
                    : "No forecast was available at the cutoff."}
                </p>
              </>
            ) : null}
          </CardContent>
        </Card>

        <div className="space-y-4">
          {basis === "trailing" ? (
            trailing.data ? (
              <BufferCard
                basis="trailing"
                buffer={trailing.data.buffer}
                coverage={trailing.data.coverage}
                adjustmentMw={trailing.data.adjusted ? trailing.data.adjustment_mw : null}
                windowStart={trailing.data.window_start}
                knownUntil={trailing.data.known_until}
              />
            ) : (
              <p className="text-muted-foreground text-sm">Loading buffer…</p>
            )
          ) : metrics.data ? (
            <BufferCard basis="retrospective" buffer={metrics.data.buffer} coverage={metrics.data.coverage} />
          ) : (
            <p className="text-muted-foreground text-sm">Loading buffer…</p>
          )}
          {metrics.data && <AccuracyCard data={metrics.data} />}
        </div>
      </div>
    </main>
  );
}
