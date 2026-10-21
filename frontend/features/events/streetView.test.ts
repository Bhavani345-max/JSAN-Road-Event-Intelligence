import { describe, expect, it } from "vitest";
import { googleMapsUrl, streetViewUrl } from "./presentation";

describe("Street View and Google Maps links", () => {
  it("opens Street View at the event's point with Google's documented Maps URL", () => {
    // Khajaguda junction, Hyderabad.
    expect(streetViewUrl(17.41823, 78.37655)).toBe(
      "https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=17.418230,78.376550",
    );
  });

  it("opens the same point on Google Maps", () => {
    expect(googleMapsUrl(51.5074, -0.1278)).toBe(
      "https://www.google.com/maps/search/?api=1&query=51.507400,-0.127800",
    );
  });

  it("keeps the point to about 10 cm, whatever precision the source gave", () => {
    expect(streetViewUrl(43.65107234567, -79.34701234567)).toContain("viewpoint=43.651072,-79.347012");
  });
});
