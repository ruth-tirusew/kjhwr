/** ISO-style UTC timestamps everywhere, so no locale ambiguity (2026-11-02, never 02/11/2026). */
export const fmtSeconds = (iso: string) => new Date(iso).toISOString().slice(0, 19).replace("T", " ") + " UTC";
export const fmtMinute = (iso: string) => new Date(iso).toISOString().slice(0, 16).replace("T", " ") + " UTC";
export const hoursBetween = (from: string, to: string) => ((Date.parse(to) - Date.parse(from)) / 36e5).toFixed(1);

export const mw = (v: number | null) => (v === null ? "n/a" : `${Math.round(v).toLocaleString("en-GB")} MW`);
export const signedMw = (v: number | null) =>
  v === null ? "n/a" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(Math.round(v)).toLocaleString("en-GB")} MW`;
