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
