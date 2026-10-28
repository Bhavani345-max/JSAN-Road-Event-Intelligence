"use client";

import { useEffect, useState } from "react";
import { listUsers, waitingCount } from "./users";

/** Confirmed registrations waiting for a decision, for an administrator's header badge (decision 0045). */
export function useWaitingRegistrations(enabled: boolean): number {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    listUsers()
      .then((accounts) => !cancelled && setCount(waitingCount(accounts)))
      // The badge is a convenience: User management itself reports errors.
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [enabled]);
  return enabled ? count : 0;
}
