"use client";

import type { ProductCardBlock, SpecCompareBlock } from "@/lib/contracts/ecommerce-blocks";
import { ProductCard } from "@/components/blocks/product-card";
import { SpecCompareTable } from "@/components/blocks/spec-compare-table";

/**
 * Renderer for module-emitted blocks attached to a chat message's
 * `metadata.blocks`. The ecommerce module's
 * `chat_stream_bridge.iter_ecommerce_router_stream_events` sets this
 * field on `message.completed` events when the controlled router has
 * dispatched to the ecommerce lane.
 *
 * The renderer is intentionally permissive: any block with an unknown
 * `type` is silently skipped so that adding a new block type on the
 * Python side never breaks the chat UI. Currently we render
 * `product_card` (laid out as a grid below the assistant text) and
 * `spec_compare` (a full-width table). The function returns `null`
 * when `metadata.blocks` is missing or empty, so it can safely be
 * dropped into the existing assistant-message JSX.
 */

type AnyMessageBlock = ProductCardBlock | SpecCompareBlock;

function isProductCardBlock(value: unknown): value is ProductCardBlock {
  if (!value || typeof value !== "object") return false;
  return (value as { type?: unknown }).type === "product_card";
}

function isSpecCompareBlock(value: unknown): value is SpecCompareBlock {
  if (!value || typeof value !== "object") return false;
  return (value as { type?: unknown }).type === "spec_compare";
}

export function MessageBlocks({ blocks }: { blocks: unknown }) {
  if (!Array.isArray(blocks) || blocks.length === 0) {
    return null;
  }

  const productCards: ProductCardBlock[] = [];
  const specTables: SpecCompareBlock[] = [];
  for (const block of blocks as AnyMessageBlock[]) {
    if (isProductCardBlock(block)) {
      productCards.push(block);
    } else if (isSpecCompareBlock(block)) {
      specTables.push(block);
    }
  }

  if (productCards.length === 0 && specTables.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 space-y-4">
      {productCards.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {productCards.map((block) => (
            <ProductCard key={block.product_id} block={block} />
          ))}
        </div>
      ) : null}
      {specTables.map((block, index) => (
        <SpecCompareTable key={`spec-${index}`} block={block} />
      ))}
    </div>
  );
}
