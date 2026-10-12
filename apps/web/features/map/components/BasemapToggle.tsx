import { BASEMAPS, type Basemap } from "@/lib/config";

const BASEMAP_LABELS: Record<Basemap, string> = {
  map: "Map",
  satellite: "Satellite",
};

interface BasemapToggleProps {
  value: Basemap;
  onChange: (basemap: Basemap) => void;
}

export default function BasemapToggle({ value, onChange }: BasemapToggleProps) {
  return (
    <div
      role="group"
      aria-label="Basemap"
      className="inline-flex rounded-xl bg-white/95 p-1 shadow-md ring-1 ring-slate-900/10 backdrop-blur"
    >
      {BASEMAPS.map((basemap) => {
        const isActive = basemap === value;
        return (
          <button
            key={basemap}
            type="button"
            aria-pressed={isActive}
            onClick={() => onChange(basemap)}
            className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-brand-400 ${
              isActive
                ? "bg-brand-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-brand-50 hover:text-brand-700"
            }`}
          >
            {BASEMAP_LABELS[basemap]}
          </button>
        );
      })}
    </div>
  );
}
