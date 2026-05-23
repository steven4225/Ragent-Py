/**
 * Shared types for the shopper workbench preview.
 *
 * The workbench is intentionally a thin presentation layer over the
 * existing `/api/preview/ecommerce/*` endpoints — no backend changes.
 * These types live here (not under `lib/contracts`) because they are
 * purely presentational (Task entries, filter state, advisor state)
 * and should not be confused with the wire-shape mirrors that already
 * live in `lib/contracts/ecommerce-blocks.ts`.
 */

import type { EcommerceProductCategory } from "@/lib/contracts/ecommerce-blocks";

/** A predefined shopping starting-point shown in the hero. */
export interface TaskEntry {
  id: string;
  /** Short title — fits on a card in one line. */
  title: string;
  /** One-sentence reason a shopper would pick this. */
  subtitle: string;
  /** Category filter to apply on click. `null` means "any". */
  category: EcommerceProductCategory | null;
  /** Inclusive max price (USD). Undefined means no cap. */
  maxPrice?: number;
  /** Inclusive min price (USD). Undefined means no floor. */
  minPrice?: number;
  /** Seed query string used for the AI advisor. */
  query: string;
  /** Tone token used by the card hero band. */
  tone: "indigo" | "emerald" | "amber" | "rose" | "sky" | "violet";
}

/** Two- to three-thousand-dollar shopping budget bands. */
export interface PriceBand {
  id: string;
  label: string;
  /** Inclusive lower bound. */
  min?: number;
  /** Inclusive upper bound. */
  max?: number;
}

/** Live filter state held by the workbench page. */
export interface FilterState {
  category: EcommerceProductCategory | null;
  priceBandId: string;
  brand: string | null;
  /** Free-text refine string that augments the seed query. */
  refine: string;
}

/** Streaming AI advisor state. */
export interface AdvisorState {
  /** Whether a stream is in flight. */
  status: "idle" | "streaming" | "done" | "error";
  /** Latest streamed text (accumulated). */
  text: string;
  /** Last question that was asked. */
  question: string;
  /** Optional error message. */
  error: string | null;
  /** Provider name (for transparency, shown small). */
  provider: string | null;
  /** Model id (for transparency, shown small). */
  model: string | null;
}
