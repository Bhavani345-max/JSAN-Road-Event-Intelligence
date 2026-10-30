import { useState } from "react";
import { eventImage, type RoadEvent } from "../model";
import { getEventTypeColor, getEventTypeLabel } from "../presentation";
import CategoryIcon from "./CategoryIcon";

/**
 * A publisher's image, loaded lazily straight from the publisher's own site
 * (decision 0050): REI never copies or re-serves it, which next/image would.
 * A grey pulse shows until it arrives; `onFail` replaces it if it cannot load
 * (moved, blocked by the publisher, offline).
 */
export function SourcePicture({
  url,
  className,
  onFail,
}: {
  url: string;
  className: string;
  onFail: () => void;
}) {
  const [loaded, setLoaded] = useState(false);
  return (
    <>
      {!loaded && <span aria-hidden="true" className="absolute inset-0 animate-pulse bg-slate-200" />}
      {/* eslint-disable-next-line @next/next/no-img-element -- see above: never proxied through REI */}
      <img
        src={url}
        alt=""
        loading="lazy"
        decoding="async"
        onLoad={() => setLoaded(true)}
        onError={onFail}
        className={`relative ${className}`}
      />
    </>
  );
}

/** The category's icon on a neutral tile: says what kind of event it is, never shows one. */
function CategoryTile({ event, note }: { event: RoadEvent; note: string }) {
  return (
    <span
      className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg bg-slate-50 ring-1 ring-inset ring-slate-200"
      style={{ color: getEventTypeColor(event.eventType) }}
      title={note}
      data-thumbnail="category"
    >
      <CategoryIcon eventType={event.eventType} className="h-7 w-7" />
    </span>
  );
}

/**
 * An event card's 64×64 thumbnail: the image published with the source article
 * when the publisher permits showing it, otherwise the category's icon.
 */
export default function EventThumbnail({ event }: { event: RoadEvent }) {
  const image = eventImage(event);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const category = getEventTypeLabel(event.eventType);

  if (!image?.url || failedUrl === image.url) {
    const why = image?.url ? "the source image could not be loaded" : "no source image can be shown";
    return <CategoryTile event={event} note={`${category} icon, not a photo: ${why}`} />;
  }
  return (
    <span
      className="relative block h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-100"
      title={`Image published with the article by ${image.sourceName}. It may be a file photo.`}
      data-thumbnail="source"
    >
      <SourcePicture
        url={image.url}
        className="h-full w-full object-cover"
        onFail={() => setFailedUrl(image.url)}
      />
      <span aria-hidden="true" className="absolute inset-0 rounded-lg ring-1 ring-inset ring-slate-900/10" />
    </span>
  );
}
