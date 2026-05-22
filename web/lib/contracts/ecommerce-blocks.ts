/**
 * Hand-mirrored TS shape for the Python-side `ProductCardBlock` and
 * preview endpoint payloads. Python is the source of truth — see
 * `src/ragent_python/modules/ecommerce/blocks.py` and
 * `src/ragent_python/api/internal_ecommerce.py`. Step E will replace
 * these definitions with `pydantic → JSON Schema → quicktype` generated
 * artifacts; until then this file is kept tiny and explicit so a
 * mismatch is easy to spot.
 */

export interface ProductSpecItem {
  label: string;
  value: string;
}

export interface ProductCardBlock {
  type: "product_card";
  product_id: string;
  name: string;
  brand: string;
  category: string;
  price_usd: number;
  summary: string;
  image_url: string;
  release_year: number;
  specs: ProductSpecItem[];
}

export interface EcommerceSearchFilters {
  brand?: string | null;
  category?: string | null;
  min_price_usd?: number | null;
  max_price_usd?: number | null;
  min_ram_gb?: number | null;
  min_release_year?: number | null;
}

export interface EcommerceSearchRequest {
  query: string;
  filters?: EcommerceSearchFilters;
  limit?: number;
}

export interface EcommerceSearchResponse {
  source: "ecommerce-catalog-preview";
  query: string;
  total: number;
  blocks: ProductCardBlock[];
}

export const ECOMMERCE_PRODUCT_CATEGORIES = [
  "laptop",
  "phone",
  "tablet",
  "earbuds",
  "monitor",
] as const;

export type EcommerceProductCategory = (typeof ECOMMERCE_PRODUCT_CATEGORIES)[number];

export interface SpecCompareColumn {
  product_id: string;
  name: string;
  brand: string;
  category: string;
  image_url: string;
}

export interface SpecCompareRow {
  label: string;
  values: string[];
  has_data: boolean;
}

export interface SpecCompareBlock {
  type: "spec_compare";
  columns: SpecCompareColumn[];
  rows: SpecCompareRow[];
  placeholder: string;
}

export interface EcommerceCompareRequest {
  product_ids: string[];
}

export interface EcommerceCompareResponse {
  source: "ecommerce-compare-preview";
  requested_ids: string[];
  resolved_ids: string[];
  missing_ids: string[];
  truncated: boolean;
  block: SpecCompareBlock;
}

export const SPEC_COMPARE_MAX_PRODUCTS = 4;

export interface EcommerceChatRequest {
  query: string;
  filters?: EcommerceSearchFilters;
  retrieval_limit?: number;
}

export interface EcommerceChatAnswer {
  text: string;
  provider: string;
  model?: string | null;
  finish_reason: string;
  input_tokens?: number | null;
  output_tokens?: number | null;
}

export interface EcommerceChatResponse {
  source: "ecommerce-chat-preview";
  query: string;
  retrieved_product_ids: string[];
  blocks: ProductCardBlock[];
  answer: EcommerceChatAnswer;
}

export interface EcommerceChatStreamRetrievalEvent {
  type: "retrieval";
  query: string;
  retrieved_product_ids: string[];
  blocks: ProductCardBlock[];
}

export interface EcommerceChatStreamDeltaEvent {
  type: "delta";
  text: string;
}

export interface EcommerceChatStreamDoneEvent {
  type: "done";
  provider: string;
  model?: string | null;
  finish_reason: string;
  input_tokens?: number | null;
  output_tokens?: number | null;
}

export type EcommerceChatStreamEvent =
  | EcommerceChatStreamRetrievalEvent
  | EcommerceChatStreamDeltaEvent
  | EcommerceChatStreamDoneEvent;
