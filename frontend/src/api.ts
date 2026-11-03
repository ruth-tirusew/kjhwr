const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type ForecastRow = {
  target_time: string;
  publish_time: string | null;
  forecast_mw: number | null;
  adjusted_mw: number | null;
  actual_mw: number | null;
};

type SnapshotMeta = { snapshot_id: string; fetched_at: string };

export type Coverage = {
  targets: number;
  scored: number;
  off_forecast_grid: number;
  no_forecast: number;
  no_actual: number;
};

export type ErrorMetrics = {
  n: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  p50_abs: number | null;
  p90_abs: number | null;
  p95_abs: number | null;
};

export type Buffer = { quantile: number; n: number; n_shortfall: number; buffer_mw: number | null };

export type ForecastResponse = SnapshotMeta & {
  cutoff: string;
  coverage: Coverage;
  metrics: ErrorMetrics;
  adjustment_mw: number | null;
  adjusted_metrics: ErrorMetrics;
  rows: ForecastRow[];
};

export type BufferResponse = SnapshotMeta & {
  basis: "trailing";
  adjusted: boolean;
  adjustment_mw: number | null;
  window_start: string;
  known_until: string;
  coverage: Coverage;
  buffer: Buffer;
};

export type MetricsResponse = SnapshotMeta & {
  coverage: Coverage;
  metrics: ErrorMetrics;
  buffer: Buffer;
};

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const getForecast = (day: string, cutoff: string) =>
  get<ForecastResponse>(`/api/forecast/${day}?cutoff=${encodeURIComponent(cutoff)}`);

export const getMetrics = (start: string, end: string, cutoff: string, quantile: number) =>
  get<MetricsResponse>(
    `/api/metrics?start=${start}&end=${end}&cutoff=${encodeURIComponent(cutoff)}&quantile=${quantile}`,
  );

export const getTrailingBuffer = (day: string, cutoff: string, quantile: number, adjust: boolean) =>
  get<BufferResponse>(`/api/buffer/${day}?cutoff=${encodeURIComponent(cutoff)}&quantile=${quantile}&adjust=${adjust}`);
