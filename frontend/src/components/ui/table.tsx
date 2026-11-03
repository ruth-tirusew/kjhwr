import type * as React from "react";
import { cn } from "@/lib/utils";

export function Table({ className, ...props }: React.ComponentProps<"table">) {
  return <table className={cn("w-full text-sm", className)} {...props} />;
}

export function Row({ className, ...props }: React.ComponentProps<"tr">) {
  return <tr className={cn("border-b last:border-b-0", className)} {...props} />;
}

export function Head({ className, ...props }: React.ComponentProps<"th">) {
  return <th scope="row" className={cn("text-muted-foreground py-2 text-left font-normal", className)} {...props} />;
}

export function Cell({ className, ...props }: React.ComponentProps<"td">) {
  return <td className={cn("py-2 text-right font-mono tabular-nums", className)} {...props} />;
}
