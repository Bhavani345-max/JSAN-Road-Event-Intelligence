# 0050 — Event cards: 64×64 thumbnails; a source article's image only with the publisher's permission

**Status:** 30 October 2026. Code local, tested, for the user to push. No
migration, no ingestion change, no Railway setting. Nothing is fetched,
stored or changed: images are read from the evidence already stored.

## Context

The user asked (30 October 2026) for event cards with a small thumbnail, the
category, city and road, validation status, GIS status, publication date and
source, and for the card to show the image published with the event's source
article, but only where that image may be used. No Google or search-engine image
copies, no stock images, and no image matched by category or headline. If
permission, attribution or ownership is uncertain, the image is not shown.

What was found:

- No image field existed anywhere (database, API, console).
- The RSS connector keeps an item's title, link, summary and body markup. It
  does not keep `<enclosure>`, `media:content` or `media:thumbnail`. The search
  and article-page readers do not keep image fields either.
- In the local database, 63 of 43,146 listed events had an image in their
  stored article markup: Telangana Today 39, NewsMeter 4 (connected), and
  Deccan Chronicle 10, The Hans India 5, Siasat 5 (terms forbid REI's use, or
  removed from REI). Every other event comes from an official feed with no
  article and no picture.
- Feeds on 30 October 2026: Telangana Today puts the featured image
  (`wp-post-image`) in the article markup, with no caption or credit. NewsMeter
  adds an `<enclosure type="image/webp">` lead image (not stored). SAnews has
  none. No feed has `media:content`, `media:thumbnail` or `media:credit`.

The publishers' terms, read on 30 October 2026:

- **Telangana Today:** its "Terms & Conditions" page holds no terms, only
  "© Copyrights 2024 TELANGANA PUBLICATIONS PVT. LTD. All rights reserved."
- **NewsMeter:** only a privacy policy, and no terms of use. Its feed's copyright
  line says "NewsMeter".
- **SAnews:** its user policy lets *media* use its photographs, "sourced to the
  DOC", while stories are credited to SAnews. REI is not media, and the credit
  line is unclear.
- **PIB:** its copyright policy could not be read again to confirm it covers
  photographs (the page answers automated readers with HTTP 403).

None grants REI permission to show its images.

## Decision

1. **Thumbnails, read-only.** `app/services/article_image.py` finds the lead
   image in the stored article markup when the API answers. That is the
   featured image, or else the first picture that is not a tracking pixel or
   inline data. The API adds `evidence.image` (and `image` on each merged
   report's evidence) with status `AVAILABLE`, `WITHHELD` or `NONE`. The field is
   additive: an older console ignores it, and the new console treats its
   absence as no image.
2. **Permission first.** An image is `AVAILABLE` only when all of these hold:
   - its source is listed in `IMAGE_PERMISSIONS` with the words that grant it,
     the credit line they require and the publisher's own image hosts;
   - the registry does not record the source's terms as restricting REI's use;
   - the image is served over https;
   - the image is on one of those hosts.

   Otherwise it is `WITHHELD`, its address is not sent, and `reason` says why.
   `IMAGE_PERMISSIONS` is **empty**: every card shows its category icon.
   Deccan Chronicle, Siasat, The Hans India, The Hindu and Mid-day can never be
   shown, even if listed, because their terms are recorded as restricting REI.
3. **Nothing made up.** Caption is the publisher's `<figcaption>`; alt text is
   the publisher's. Credit stays empty unless the source states one. The
   details panel says "Photo credit: not stated by the source".
4. **Shown from the publisher's site.** The console loads a permitted image
   directly from the publisher, lazily. REI never copies, stores or re-serves
   it: plain `<img>`, not `next/image`, which would proxy it. A publisher that
   blocks other sites from showing its images is respected: the card falls back
   to the icon.
5. **The card** keeps the blue sidebar, the white card, the category stripe and
   the selected-card ring. The new layout:
   - left: the 64×64 thumbnail;
   - next to it: the headline across the full width, then city · road, then
     category, severity and validation status;
   - full width below: the event time and the GIS status;
   - bottom row: the source, "Published …" (or "Updated …" for official feeds),
     extra sources, possible duplicate, cited authority and confidence.

   The height is about what it was: the thumbnail sits beside rows that
   existed. With no permitted image, the tile is the category's line icon on a
   neutral tile. Its tooltip says "icon, not a photo".
6. **Details panel:** the larger image (click to enlarge, Escape to close),
   "Image published with the article by …", the credit, the permission it is
   shown under, the article link, and "May be a file photo, not necessarily a
   photograph of this specific event." For a withheld image, one line says why
   it is not shown.

## Not done

- **NewsMeter's lead image for new articles (step 2):** stopped, as the user
  instructed, because NewsMeter's terms do not establish permission. The RSS
  connector is unchanged.
- **Open Graph and Twitter images:** not read. REI reads no article page for
  images, and backfilling old events would mean fetching thousands of pages and
  a new table.
- **Google/Serper image results:** never used. They are a search engine's
  copies, not the publisher's article image.

## When a publisher gives permission

Add the publisher to `IMAGE_PERMISSIONS` with:

- the granting words, with where and when they were read;
- the credit line they require;
- its image hosts.

Its stored article images then show on the next page load. No data changes.
Keeping enclosure or media images for new articles is a separate ingestion
change, which needs the user's approval.
