import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
    {
        variants: {
            variant: {
                default:
                    "border-transparent bg-zinc-800 text-zinc-100 hover:bg-zinc-800/80",
                secondary:
                    "border-transparent bg-zinc-800 text-zinc-100 hover:bg-zinc-800/80",
                destructive:
                    "border-transparent bg-red-900/50 text-red-200 hover:bg-red-900/80",
                outline: "text-zinc-200 border-zinc-700",
                success:
                    "border-transparent bg-green-900/50 text-green-200 hover:bg-green-900/80",
                warning:
                    "border-transparent bg-yellow-900/50 text-yellow-200 hover:bg-yellow-900/80",
                info:
                    "border-transparent bg-blue-900/50 text-blue-200 hover:bg-blue-900/80",
            },
        },
        defaultVariants: {
            variant: "default",
        },
    }
)

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
    return (
        <div className={cn(badgeVariants({ variant }), className)} {...props} />
    )
}

export { Badge, badgeVariants }
