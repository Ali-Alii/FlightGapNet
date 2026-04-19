import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

/**
 * TrajectoryMap — Fixed Leaflet import (no more window.L hack).
 * Properly cleans up the map instance on unmount to prevent double-mount issues.
 */
export default function TrajectoryMap({ data }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layersRef = useRef([]);

  // Init map once
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    mapInstanceRef.current = L.map(mapRef.current, {
      center: [48, 10],
      zoom: 5,
      zoomControl: true,
      attributionControl: false,
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 18,
      subdomains: "abcd",
    }).addTo(mapInstanceRef.current);

    // Minimal attribution
    L.control
      .attribution({ position: "bottomright", prefix: "" })
      .addTo(mapInstanceRef.current)
      .setPrefix('<span style="color:#3a5a7a;font-size:9px">© CartoDB</span>');

    return () => {
      // Cleanup on unmount
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update layers when data changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !data) return;

    // Remove old layers
    layersRef.current.forEach((l) => {
      try { map.removeLayer(l); } catch (_) {}
    });
    layersRef.current = [];

    const addPoly = (coords, color, weight, dash = "") => {
      if (!coords || coords.length < 2) return null;
      const latlngs = coords.map((p) => [p.lat, p.lon]);
      const poly = L.polyline(latlngs, { color, weight, dashArray: dash, opacity: 0.9 }).addTo(map);
      layersRef.current.push(poly);
      return poly;
    };

    addPoly(data.full_track, "#1a3a5c", 2);
    addPoly(data.true_gap, "#ffffff", 2, "4 4");
    addPoly(data.baseline_pred, "#f5a623", 2, "6 3");
    const modelPoly = addPoly(data.model_pred, "#00c8ff", 3);

    if (modelPoly) {
      map.fitBounds(modelPoly.getBounds(), { padding: [50, 50] });
    } else if (data.full_track?.length) {
      const allCoords = data.full_track.map((p) => [p.lat, p.lon]);
      map.fitBounds(L.latLngBounds(allCoords), { padding: [40, 40] });
    }

    // Start / end markers
    if (data.full_track?.length) {
      const first = data.full_track[0];
      const last = data.full_track[data.full_track.length - 1];

      const dot = (color) =>
        L.divIcon({
          html: `<div style="width:8px;height:8px;background:${color};border-radius:50%;border:2px solid #060d18;box-shadow:0 0 6px ${color}"></div>`,
          iconSize: [8, 8],
          className: "",
        });

      layersRef.current.push(
        L.marker([first.lat, first.lon], { icon: dot("#00e87a") }).addTo(map),
        L.marker([last.lat, last.lon], { icon: dot("#ff3355") }).addTo(map)
      );
    }
  }, [data]);

  return (
    <div className="relative">
      <div
        ref={mapRef}
        className="w-full rounded border border-[#0e2040]"
        style={{ height: 400 }}
      />
      {/* Legend */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-[#060d18]/90 border border-[#0e2040] rounded p-3 space-y-1.5 font-mono text-[10px]">
        {[
          { color: "#1a3a5c", label: "Observed track" },
          { color: "#ffffff", label: "True gap (hidden)", dash: true },
          { color: "#f5a623", label: "Baseline (linear)", dash: true },
          { color: "#00c8ff", label: "Model prediction" },
        ].map(({ color, label, dash }) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className="w-5 h-0.5"
              style={{
                background: dash
                  ? `repeating-linear-gradient(to right,${color} 0,${color} 3px,transparent 3px,transparent 6px)`
                  : color,
              }}
            />
            <span className="text-[#3a5a7a]">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}