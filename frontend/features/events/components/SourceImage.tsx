import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { eventImage, type ArticleImage, type RoadEvent } from "../model";
import { getSiteName } from "../presentation";
import { SourcePicture } from "./EventThumbnail";

/** Said wherever a source image is shown: a news photo may not show this event. */
export const FILE_PHOTO_WARNING = "May be a file photo, not necessarily a photograph of this specific event.";

/** The image full size over the page; Escape, the close button or a click outside closes it. */
function ImagePreview({ image, onClose }: { image: ArticleImage; onClose: () => void }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Image published with the article by ${image.sourceName}`}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-slate-950/85 p-4"
      onClick={onClose}
    >
      <button
        type="button"
        onClick={onClose}
        autoFocus
        aria-label="Close the image"
        className="absolute right-3 top-3 flex h-10 w-10 cursor-pointer items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
      >
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
          <path d="m5 5 10 10M15 5 5 15" strokeLinecap="round" />
        </svg>
      </button>
      {/* eslint-disable-next-line @next/next/no-img-element -- from the publisher's site, never proxied through REI */}
      <img
        src={image.url!}
        alt={image.altText ?? ""}
        className="max-h-[78dvh] max-w-full rounded-lg object-contain shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      />
      <p className="max-w-xl text-center text-xs leading-relaxed text-slate-300">
        Image published with the article by {image.sourceName}. {FILE_PHOTO_WARNING}
      </p>
    </div>,
    document.body,
  );
}

/**
 * The image published with the event's source article, with its attribution,
 * the article link and the file-photo warning; or, when the article has an
 * image REI may not show, why not. Nothing for an article without one.
 */
export default function SourceImage({ event }: { event: RoadEvent }) {
  const image = eventImage(event);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);

  if (!image?.url) {
    const withheld = event.evidence?.image.status === "withheld" ? event.evidence.image : null;
    if (!withheld) return null;
    return (
      <p className="text-[11px] leading-relaxed text-slate-500" data-source-image="withheld">
        <span className="font-semibold text-slate-600">The article&rsquo;s image is not shown.</span>{" "}
        {withheld.reason}
      </p>
    );
  }

  const failed = failedUrl === image.url;
  const site = getSiteName(image.sourceUrl);
  return (
    <figure className="overflow-hidden rounded-lg bg-white ring-1 ring-inset ring-slate-200" data-source-image="shown">
      {failed ? (
        <div className="flex h-40 items-center justify-center bg-slate-50 px-4 text-center text-xs text-slate-400">
          The image could not be loaded from {image.sourceName}.
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setPreviewing(true)}
          className="relative block h-40 w-full cursor-zoom-in overflow-hidden bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
          aria-label="Enlarge the article image"
        >
          <SourcePicture
            url={image.url}
            className="h-full w-full object-cover"
            onFail={() => setFailedUrl(image.url)}
          />
        </button>
      )}
      <figcaption className="space-y-1 px-3 py-2.5 text-[11px] leading-relaxed text-slate-500">
        {image.caption && <p className="text-xs text-slate-700">{image.caption}</p>}
        <p>
          <span className="font-semibold text-slate-700">
            Image published with the article by {image.sourceName}
          </span>
          {image.attribution && image.attribution !== image.sourceName && <> · Credit: {image.attribution}</>}
        </p>
        <p>
          Photo credit:{" "}
          {image.credit ?? <span className="italic text-slate-400">not stated by the source</span>}
        </p>
        <p role="note" className="font-medium text-amber-800">
          {FILE_PHOTO_WARNING}
        </p>
        {image.licence && (
          <details className="text-slate-500">
            <summary className="cursor-pointer select-none font-medium text-slate-600">
              Permission to show it
            </summary>
            <p className="mt-0.5">{image.licence}</p>
          </details>
        )}
        {image.sourceUrl && (
          <a
            href={image.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-800 hover:underline"
          >
            Open article{site && ` on ${site}`}
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-3 w-3" aria-hidden="true">
              <path d="M6 3h7v7M13 3 4 12" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
        )}
      </figcaption>
      {previewing && !failed && <ImagePreview image={image} onClose={() => setPreviewing(false)} />}
    </figure>
  );
}
