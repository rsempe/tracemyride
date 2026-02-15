"use client";

import dynamic from "next/dynamic";
import { RoutePanel } from "@/components/RoutePanel";
import { ElevationChart } from "@/components/ElevationChart";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default function Home() {
  return (
    <div className="h-screen w-screen flex">
      <RoutePanel />
      <div className="flex-1 relative">
        <MapView />
        <ElevationChart />
      </div>
    </div>
  );
}
