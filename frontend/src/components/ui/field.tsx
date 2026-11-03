import type * as React from "react";
import { cn } from "@/lib/utils";

const control =
  "border-input bg-background h-9 w-full border px-3 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function Label({ className, ...props }: React.ComponentProps<"label">) {
  return <label className={cn("flex flex-col gap-1.5 text-xs font-medium", className)} {...props} />;
}

export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return <input className={cn(control, className)} {...props} />;
}

export function Select({ className, ...props }: React.ComponentProps<"select">) {
  return <select className={cn(control, className)} {...props} />;
}
