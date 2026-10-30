import type { EventType } from "../model";

/**
 * A line icon for each kind of event: a symbol of the category, never a
 * picture of an event. Drawn on a 24-unit grid in the current text colour.
 */
const BARRIER = (
  <>
    <rect x="3" y="7.5" width="18" height="5.5" rx="1" />
    <path d="M8 7.5 5.5 13M13 7.5 10.5 13M18 7.5 15.5 13M6.5 13v6.5M17.5 13v6.5M4.5 19.5h4M15.5 19.5h4" />
  </>
);
const CONE = <path d="M9.6 4.5h4.8L18.5 20h-13L9.6 4.5ZM8.2 10h7.6M6.9 15h10.2M3.5 20h17" />;
const WAVES = (
  <path d="M3 8.5c2 0 2.4-1.5 4.5-1.5S10 8.5 12 8.5s2.4-1.5 4.5-1.5S19 8.5 21 8.5M3 13.5c2 0 2.4-1.5 4.5-1.5s2.5 1.5 4.5 1.5 2.4-1.5 4.5-1.5 2.5 1.5 4.5 1.5M3 18.5c2 0 2.4-1.5 4.5-1.5s2.5 1.5 4.5 1.5 2.4-1.5 4.5-1.5 2.5 1.5 4.5 1.5" />
);
const ROAD = <path d="M8.5 3 5 21M15.5 3 19 21M12 4v2.5M12 10.5v3M12 17.5V20" />;

const ICONS: Record<EventType, React.ReactNode> = {
  PLANNED_ROAD_CLOSURE: BARRIER,
  EMERGENCY_ROAD_CLOSURE: (
    <>
      {BARRIER}
      <path d="M12 2v2.5" />
    </>
  ),
  WEATHER_CLOSURE: (
    <path d="M7.5 15h9a3.5 3.5 0 0 0 .4-7 5 5 0 0 0-9.7-1.2A4.1 4.1 0 0 0 7.5 15ZM9 18l-1 2.5M13 18l-1 2.5M17 18l-1 2.5" />
  ),
  ROAD_CONSTRUCTION: CONE,
  ROAD_WORKS: CONE,
  TRAFFIC_DIVERSION: <path d="M6 20.5V14a4 4 0 0 1 4-4h8.5M15.5 7l3 3-3 3M6 3.5v4" />,
  FLOODING: WAVES,
  WATERLOGGING: (
    <path d="M12 3.5s-4.5 4.8-4.5 7.9a4.5 4.5 0 0 0 9 0C16.5 8.3 12 3.5 12 3.5ZM3 20c2 0 2.4-1.5 4.5-1.5S10 20 12 20s2.4-1.5 4.5-1.5S19 20 21 20" />
  ),
  ACCIDENT: (
    <>
      <path d="M3.5 16.5v-3.2l2.4-4.3h7.6l3.4 4.3h2.6a1 1 0 0 1 1 1v2.2M6.5 13.3h10.4M15.5 3.5l.4 2.6M19.5 4.5l-1.6 2.1M21.5 8.2l-2.5.4" />
      <circle cx="7.5" cy="17" r="1.8" />
      <circle cx="16.5" cy="17" r="1.8" />
    </>
  ),
  ROAD_HAZARD: <path d="M12 4 21.5 20h-19L12 4ZM12 10v4.5M12 17.2v.1" />,
  PUBLIC_PROCESSION: <path d="M6 21V3.5M6 4.5h11l-2.2 3.7L17 12H6" />,
  SPECIAL_EVENT: (
    <path d="m12 3.8 2.5 5.1 5.6.8-4 3.9.9 5.6-5-2.6-5 2.6.9-5.6-4-3.9 5.6-.8L12 3.8Z" />
  ),
  MARATHON: (
    <>
      <circle cx="12" cy="13.5" r="7" />
      <path d="M12 13.5V9.5M10 3h4M12 3v3.5M18 6.5l1.3-1.3" />
    </>
  ),
  SPORTING_EVENT: (
    <path d="M8 4h8v5a4 4 0 0 1-8 0V4ZM8 5.5H5a3 3 0 0 0 3.3 3.5M16 5.5h3a3 3 0 0 1-3.3 3.5M12 13v4M9 20.5h6M10 17h4v3.5h-4z" />
  ),
  BRIDGE_TUNNEL_RESTRICTION: <path d="M2.5 9.5h19M4 9.5v10M20 9.5v10M7 19.5V16a5 5 0 0 1 10 0v3.5" />,
  LANE_RESTRICTION: <path d="M4.5 3v18M19.5 3v18M12 4v3M12 10.5v3M12 17v3M14.5 9l3 3m0-3-3 3" />,
  VIP_MOVEMENT: <path d="M12 3.5 19 6v5.5c0 4.3-3 7.6-7 9-4-1.4-7-4.7-7-9V6l7-2.5Z" />,
  TURN_RESTRICTION: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9 17v-4.5a3 3 0 0 1 3-3h3.5M13.5 7.5l2 2-2 2M5.6 18.4 18.4 5.6" />
    </>
  ),
};

export default function CategoryIcon({
  eventType,
  className,
}: {
  eventType: EventType | null;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {eventType ? ICONS[eventType] : ROAD}
    </svg>
  );
}
