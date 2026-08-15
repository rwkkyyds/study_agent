import * as React from "react";
import { cn } from "@/lib/utils";

const ScrollArea = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <div className={cn("relative overflow-hidden", className)} {...props}>
        <div
          ref={ref}
          className="h-full w-full overflow-auto [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-track]:bg-transparent"
        >
          {children}
        </div>
      </div>
    );
  },
);
ScrollArea.displayName = "ScrollArea";

export { ScrollArea };