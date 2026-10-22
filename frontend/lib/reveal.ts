/**
 * Bring an element into view inside its own scroll area only.
 *
 * `element.scrollIntoView()` scrolls every scrollable ancestor, the page
 * included, which shifted the whole console up and left a white strip at the
 * bottom. This scrolls just the nearest scroll container and never the page.
 */

type Edges = { top: number; bottom: number };

/** How far a scroll area must move so `item` sits inside `view` (0 when it already does). */
export function revealDelta(item: Edges, view: Edges, margin = 8): number {
  if (item.top < view.top + margin) return item.top - view.top - margin;
  if (item.bottom > view.bottom - margin) {
    // An item taller than the view is aligned by its top edge.
    const down = item.bottom - view.bottom + margin;
    const toTop = item.top - view.top - margin;
    return Math.min(down, toTop);
  }
  return 0;
}

function nearestScroller(element: HTMLElement): HTMLElement | null {
  for (let node = element.parentElement; node && node !== document.body && node !== document.documentElement; node = node.parentElement) {
    const { overflowY } = getComputedStyle(node);
    if ((overflowY === "auto" || overflowY === "scroll") && node.scrollHeight > node.clientHeight) return node;
  }
  return null;
}

export function revealInScroller(element: HTMLElement, behavior: ScrollBehavior = "smooth"): void {
  const scroller = nearestScroller(element);
  if (!scroller) return;
  const delta = revealDelta(element.getBoundingClientRect(), scroller.getBoundingClientRect());
  if (delta !== 0) scroller.scrollBy({ top: delta, behavior });
}
