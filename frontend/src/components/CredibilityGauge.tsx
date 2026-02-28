"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle, HelpCircle } from "lucide-react";

interface CredibilityGaugeProps {
    score: number; // 0.0 to 1.0 (Probability of being FAKE)
    className?: string;
}

export function CredibilityGauge({ score, className }: CredibilityGaugeProps) {
    // Credibility is inverse of fake score
    const fakePercent = Math.round(score * 100);
    const realPercent = 100 - fakePercent;

    let statusText = "Uncertain";
    let statusColor = "text-yellow-500";
    let barColor = "bg-yellow-500";
    let Icon = HelpCircle;

    if (fakePercent >= 70) {
        statusText = "Likely Fake";
        statusColor = "text-red-500";
        barColor = "bg-red-500";
        Icon = AlertTriangle;
    } else if (fakePercent <= 30) {
        statusText = "Likely Real";
        statusColor = "text-emerald-500";
        barColor = "bg-emerald-500";
        Icon = CheckCircle;
    }

    // Calculate SVG stroke dasharray for a circular gauge
    const radius = 60;
    const circumference = 2 * Math.PI * radius;
    // We only show a half circle (180 degrees)
    const semiCircumference = circumference / 2;
    const fillAmount = (realPercent / 100) * semiCircumference;
    const dashArray = `${fillAmount} ${circumference}`;

    return (
        <div className={cn("flex flex-col items-center justify-center p-6", className)}>
            <div className="relative w-48 h-24 flex items-end justify-center overflow-hidden">
                {/* Background Arc */}
                <svg
                    className="absolute top-0 left-0 w-full h-[200%]"
                    viewBox="0 0 160 160"
                >
                    <circle
                        cx="80"
                        cy="80"
                        r={radius}
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="16"
                        className="text-slate-200 dark:text-slate-800"
                        strokeLinecap="round"
                        strokeDasharray={`${semiCircumference} ${circumference}`}
                        transform="rotate(180 80 80)"
                    />
                    {/* Foreground Arc */}
                    <circle
                        cx="80"
                        cy="80"
                        r={radius}
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="16"
                        className={cn("transition-all duration-1000 ease-out", statusColor)}
                        strokeLinecap="round"
                        strokeDasharray={dashArray}
                        transform="rotate(180 80 80)"
                    />
                </svg>

                {/* Center Text */}
                <div className="flex flex-col items-center mb-[-0.5rem] z-10 w-full bg-white dark:bg-slate-950 pt-2 rounded-t-full mt-[4rem]">
                    <span className="text-3xl font-bold tracking-tight">
                        {realPercent}%
                    </span>
                    <span className="text-xs uppercase font-semibold text-slate-500">
                        Credibility
                    </span>
                </div>
            </div>

            <div className="mt-6 flex items-center gap-2">
                <Icon className={cn("w-5 h-5", statusColor)} />
                <span className={cn("text-lg font-semibold", statusColor)}>
                    {statusText}
                </span>
            </div>
            <p className="text-sm text-slate-500 mt-1 max-w-[200px] text-center">
                Our AI estimates this article is {fakePercent}% likely to be fabricated.
            </p>
        </div>
    );
}
