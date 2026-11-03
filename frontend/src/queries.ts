import { keepPreviousData, queryOptions, useQuery } from "@tanstack/react-query";
import { getForecast, getMetrics, getTrailingBuffer } from "./api";

// Snapshots are immutable, so results only change with the inputs. Never refetch on focus.
const common = { staleTime: Infinity, placeholderData: keepPreviousData } as const;

export const forecastQuery = (day: string, cutoff: string) =>
  queryOptions({ queryKey: ["forecast", day, cutoff], queryFn: () => getForecast(day, cutoff), ...common });

export const metricsQuery = (start: string, end: string, cutoff: string, quantile: number) =>
  queryOptions({
    queryKey: ["metrics", start, end, cutoff, quantile],
    queryFn: () => getMetrics(start, end, cutoff, quantile),
    ...common,
  });

export const trailingBufferQuery = (day: string, cutoff: string, quantile: number, adjust: boolean) =>
  queryOptions({
    queryKey: ["buffer", day, cutoff, quantile, adjust],
    queryFn: () => getTrailingBuffer(day, cutoff, quantile, adjust),
    ...common,
  });

export const useTrailingBuffer = (day: string, cutoff: string, quantile: number, adjust: boolean) =>
  useQuery(trailingBufferQuery(day, cutoff, quantile, adjust));

export const useForecast = (day: string, cutoff: string) => useQuery(forecastQuery(day, cutoff));
export const useMetrics = (start: string, end: string, cutoff: string, quantile: number) =>
  useQuery(metricsQuery(start, end, cutoff, quantile));
