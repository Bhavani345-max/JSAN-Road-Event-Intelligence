import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ApiArticleImage, ApiEvent } from "@/types/api";
import { mapApiEvent } from "./api/eventRepository";
import EventList from "./components/EventList";
import SourceImage, { FILE_PHOTO_WARNING } from "./components/SourceImage";
import { eventImage, type RoadEvent } from "./model";
import { locatedApiEvent, realApiEvent } from "./testing/fixtures";

const NOW = new Date("2026-10-02T08:00:00Z");
const PHOTO = "https://news.example.com/uploads/lead-768x450.jpg";

const available: ApiArticleImage = {
  status: "AVAILABLE",
  url: PHOTO,
  source_url: "https://news.example.com/traffic-diversions",
  found_in: "article_markup",
  caption: null,
  alt_text: "Lakeview Junction",
  credit: null,
  licence: "Example Daily's image policy: 'Our photographs may be shown with credit.'",
  attribution: "Example Daily",
  reason: null,
};
const withheld: ApiArticleImage = {
  ...available,
  status: "WITHHELD",
  url: null,
  licence: null,
  attribution: null,
  reason: "Telangana Today has not given REI permission to show its images.",
};

function withImage(dto: ApiEvent, image: ApiArticleImage | undefined): RoadEvent {
  return mapApiEvent({ ...dto, evidence: dto.evidence && { ...dto.evidence, image } })!;
}

function card(...events: RoadEvent[]): string {
  return renderToStaticMarkup(
    createElement(EventList, {
      state: { status: "ready", events, now: NOW, empty: { title: "", lines: [], clearFilters: false } },
      selectedEventId: null,
      articleMatchIds: new Set<string>(),
      onSelect: () => {},
      onClearFilters: () => {},
      onRetry: () => {},
    }),
  );
}

const details = (event: RoadEvent) => renderToStaticMarkup(createElement(SourceImage, { event }));

describe("the article image as the console receives it", () => {
  it("is no image for an event from an API before images existed", () => {
    const event = mapApiEvent(realApiEvent)!;
    expect(event.evidence?.image.status).toBe("none");
    expect(eventImage(event)).toBeNull();
  });

  it("keeps a permitted image with its article, credit line and permission", () => {
    const image = withImage(realApiEvent, available).evidence!.image;
    expect(image).toMatchObject({
      status: "available",
      url: PHOTO,
      sourceUrl: "https://news.example.com/traffic-diversions",
      sourceName: "Telangana Today",
      attribution: "Example Daily",
      credit: null,
    });
  });

  it("never takes an address for an image that is not available", () => {
    const image = withImage(realApiEvent, { ...withheld, url: PHOTO }).evidence!.image;
    expect(image.status).toBe("withheld");
    expect(image.url).toBeNull();
    expect(withImage(realApiEvent, { ...available, url: null }).evidence!.image.status).toBe("none");
    expect(withImage(realApiEvent, { ...available, status: "SOMETHING_NEW" }).evidence!.image.status).toBe("none");
  });

  it("takes a merged report's image when the event's own article has none", () => {
    const event = mapApiEvent({
      ...locatedApiEvent,
      other_evidence: [
        {
          event_id: "EVT-NEWS",
          source: { source_id: "newsmeter", source_name: "NewsMeter", source_type: "RSS" },
          artifact_id: "a9",
          url: "https://news.example.com/merged",
          title: "Merged report",
          published_at: null,
          retrieved_at: null,
          how: "reviewer",
          image: { ...available, source_url: "https://news.example.com/merged" },
        },
      ],
    })!;
    expect(eventImage(event)).toMatchObject({ url: PHOTO, sourceName: "NewsMeter" });
  });
});

describe("an event card", () => {
  it("shows a permitted source image as a lazy 64×64 thumbnail", () => {
    const html = card(withImage(realApiEvent, available));
    expect(html).toContain('data-thumbnail="source"');
    expect(html).toContain(`src="${PHOTO}"`);
    expect(html).toContain('loading="lazy"');
    expect(html).toContain("h-16 w-16");
    expect(html).toContain("object-cover");
    expect(html).toContain("may be a file photo");
  });

  it("shows the category icon, never an image, when none may be shown", () => {
    for (const image of [withheld, undefined]) {
      const html = card(withImage(realApiEvent, image));
      expect(html).toContain('data-thumbnail="category"');
      expect(html).toContain("Traffic Diversion icon, not a photo: no source image can be shown");
      expect(html).not.toContain("<img");
    }
  });

  it("gives each article its own image when two share the same one", () => {
    const html = card(
      withImage(realApiEvent, available),
      withImage({ ...locatedApiEvent, source_reference: "https://news.example.com/other" }, available),
    );
    expect(html.split(`src="${PHOTO}"`).length - 1).toBe(2);
  });

  it("states the category, city and road, review status, location status, source and publication date", () => {
    const html = card(
      withImage(
        { ...locatedApiEvent, detection: { ...realApiEvent.detection!, location_class: "SOURCE_PROVIDED" } },
        undefined,
      ),
    );
    expect(html).toContain("Planned Road Closure");
    expect(html).toContain("Hyderabad");
    expect(html).toContain("Necklace Road");
    expect(html).toContain("Scheduled");
    expect(html).toContain("Location: </span>Source provided");
    expect(html).toContain("The Hindu");
    expect(html).toContain("Published 1 Oct");
  });

  it("says an event is not located when it has no position", () => {
    expect(card(mapApiEvent(realApiEvent)!)).toContain("Not located");
  });
});

describe("the event details' source image", () => {
  it("shows the image with its source, the article link, an unstated credit as such, and the file-photo warning", () => {
    const html = details(withImage(realApiEvent, available));
    expect(html).toContain(`src="${PHOTO}"`);
    expect(html).toContain("Image published with the article by Telangana Today");
    expect(html).toContain("Credit: Example Daily");
    expect(html).toContain("not stated by the source");
    expect(html).toContain(FILE_PHOTO_WARNING);
    expect(FILE_PHOTO_WARNING).toBe("May be a file photo, not necessarily a photograph of this specific event.");
    expect(html).toContain('href="https://news.example.com/traffic-diversions"');
    expect(html).toContain("Enlarge the article image");
  });

  it("says why an article's image is not shown, without showing it", () => {
    const html = details(withImage(realApiEvent, withheld));
    expect(html).toContain("The article’s image is not shown.");
    expect(html).toContain("Telangana Today has not given REI permission to show its images.");
    expect(html).not.toContain("<img");
  });

  it("is absent for an article without an image", () => {
    expect(details(withImage(realApiEvent, undefined))).toBe("");
  });
});
