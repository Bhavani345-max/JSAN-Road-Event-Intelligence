import { EVENT_TYPES, type EventType } from "@/features/events/model";
import { EVENT_TYPE_COLORS, EVENT_TYPE_LABELS } from "@/features/events/presentation";

interface MapLegendProps {
  /** The types of the events on the map; every type when not given. */
  eventTypes?: readonly EventType[];
}

export default function MapLegend({ eventTypes }: MapLegendProps) {
  const shown = eventTypes && eventTypes.length > 0
    ? EVENT_TYPES.filter((eventType) => eventTypes.includes(eventType))
    : EVENT_TYPES;
  return (
    <div className="rounded-xl bg-white/95 px-3 py-2.5 text-[11px] text-slate-600 shadow-md ring-1 ring-slate-900/10 backdrop-blur">
      <ul className="space-y-1">
        {shown.map((eventType) => (
          <li key={eventType} className="flex items-center gap-2">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: EVENT_TYPE_COLORS[eventType] }}
            />
            {EVENT_TYPE_LABELS[eventType]}
          </li>
        ))}
      </ul>
      <ul className="mt-2 space-y-1 border-t border-slate-200 pt-2">
        <li className="flex items-center gap-2">
          <span className="w-5 border-t-[3px] border-slate-500" />
          In effect
        </li>
        <li className="flex items-center gap-2">
          <span className="w-5 border-t-[3px] border-dashed border-slate-500" />
          Scheduled / unconfirmed
        </li>
      </ul>
      <ul className="mt-2 space-y-1 border-t border-slate-200 pt-2">
        <li className="flex items-center gap-2" title="The geometry the source itself publishes">
          <span className="ml-1.5 h-2.5 w-2.5 rounded-full bg-slate-500 ring-2 ring-white" />
          <span className="ml-1">Source provided</span>
        </li>
        <li className="flex items-center gap-2" title="Matched to the OSM road network; a proposal until a reviewer approves it">
          <span className="ml-1.5 h-2.5 w-2.5 rounded-full border-[2.5px] border-teal-700 bg-slate-500" />
          <span className="ml-1">GIS resolved (road network)</span>
        </li>
        <li className="flex items-center gap-2" title="Placed on the map by a reviewer">
          <span className="ml-1.5 h-2.5 w-2.5 rounded-full border-[2.5px] border-slate-900 bg-slate-500" />
          <span className="ml-1">Corrected by a reviewer</span>
        </li>
        <li className="flex items-center gap-2" title="The position of a place the source names, not of the event itself">
          <span className="ml-1.5 h-2.5 w-2.5 rounded-full border-[2.5px] border-slate-500 bg-white" />
          <span className="ml-1">Approximate (named place)</span>
        </li>
      </ul>
      <ul className="mt-2 space-y-1 border-t border-slate-200 pt-2">
        <li className="flex items-center gap-2" title="For the selected event: the places an AI reading found in the article, by their role">
          <span className="ml-1.5 h-2.5 w-2.5 rounded-full bg-slate-500 ring-2 ring-white" />
          <span className="ml-1">Selected: closed or affected place</span>
        </li>
        <li className="flex items-center gap-2" title="Where the article says traffic is sent instead">
          <span className="ml-1.5 h-2.5 w-2.5 rounded-full bg-green-600 ring-2 ring-white" />
          <span className="ml-1">Selected: diversion or alternative route</span>
        </li>
      </ul>
    </div>
  );
}
