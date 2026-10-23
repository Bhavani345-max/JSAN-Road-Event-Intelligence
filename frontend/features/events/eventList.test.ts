import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import EventList, { type EmptyListMessage } from "./components/EventList";

function emptyList(empty: EmptyListMessage): string {
  return renderToStaticMarkup(
    createElement(EventList, {
      state: { status: "ready", events: [], now: new Date("2026-10-23T08:00:00Z"), empty },
      selectedEventId: null,
      articleMatchIds: new Set<string>(),
      onSelect: () => {},
      onClearFilters: () => {},
      onRetry: () => {},
    }),
  );
}

describe("an empty event list", () => {
  it("says why it is empty, with no filter to clear when no filter is the cause", () => {
    const html = emptyList({
      title: "No events to show for South Africa",
      lines: ["1 event is awaiting location verification."],
      clearFilters: false,
    });
    expect(html).toContain("No events to show for South Africa");
    expect(html).toContain("1 event is awaiting location verification.");
    expect(html).not.toContain("Clear filters");
    expect(html).not.toContain("match your filters");
  });

  it("offers to clear the filters when they hide the events", () => {
    const html = emptyList({
      title: "No events match your filters",
      lines: ["Try a different search term or loosen the filters."],
      clearFilters: true,
    });
    expect(html).toContain("No events match your filters");
    expect(html).toContain("Clear filters");
  });
});
