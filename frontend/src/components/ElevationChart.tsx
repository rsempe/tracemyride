"use client";

import { useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useStore } from "@/lib/store";
import { useTranslation } from "@/lib/i18n";

export function ElevationChart() {
  const route = useStore((s) => s.route);
  const setHoveredRoutePoint = useStore((s) => s.setHoveredRoutePoint);
  const { t } = useTranslation();

  const profile = route?.elevation_profile;

  const handleMouseMove = useCallback(
    (state: { activeTooltipIndex?: number }) => {
      if (!profile || state.activeTooltipIndex == null) {
        setHoveredRoutePoint(null);
        return;
      }
      const filtered = profile.filter((p) => p.elevation !== null);
      const pt = filtered[state.activeTooltipIndex];
      if (pt) {
        setHoveredRoutePoint([pt.lng, pt.lat]);
      }
    },
    [profile, setHoveredRoutePoint]
  );

  const handleMouseLeave = useCallback(() => {
    setHoveredRoutePoint(null);
  }, [setHoveredRoutePoint]);

  if (!profile?.length) return null;

  const data = profile
    .filter((p) => p.elevation !== null)
    .map((p) => ({
      distance: p.distance_km,
      elevation: Math.round(p.elevation!),
    }));

  if (data.length < 2) return null;

  const minElev = Math.min(...data.map((d) => d.elevation));
  const maxElev = Math.max(...data.map((d) => d.elevation));
  const padding = Math.max((maxElev - minElev) * 0.1, 10);

  return (
    <div className="absolute bottom-4 left-4 right-4 bg-white/95 dark:bg-gray-900/95 backdrop-blur rounded-xl shadow-lg p-3 max-w-2xl mx-auto">
      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
        {t("elevationProfile")}
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <AreaChart
          data={data}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id="elevGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="distance"
            tickFormatter={(v: number) => `${v.toFixed(1)}`}
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[minElev - padding, maxElev + padding]}
            tickFormatter={(v: number) => `${v}m`}
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={45}
          />
          <Tooltip
            formatter={(value: number) => [`${value} m`, t("elevation")]}
            labelFormatter={(label: number) => `${label.toFixed(2)} km`}
            contentStyle={{ fontSize: 12 }}
          />
          <Area
            type="monotone"
            dataKey="elevation"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#elevGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
