"use client";

import { ExternalLink, Guitar, Tag } from "lucide-react";
import { ProductCard } from "@/lib/types";

const COLOR_MAP: Record<string, string> = {
  "BK": "#1a1a1a", "3TS": "#8B4513", "N": "#D4A76A", "WH": "#F5F5F5",
  "DB": "#003366", "MBL": "#1E3A5F", "MRD": "#8B0000", "RD": "#CC0000",
  "VW": "#FFF8DC", "SG": "#2E8B57", "SPI": "#FFD700", "GR": "#228B22",
  "CS": "#CD853F", "BLS": "#4169E1", "VT": "#7B68EE", "HB": "#DAA520",
  "TBK": "#2F2F2F", "SBK": "#333333", "SBL": "#4682B4", "SHB": "#B8860B",
  "CM": "#DC143C", "IB": "#00CED1", "RS": "#E9967A", "YL": "#FFD700",
  "BL": "#4169E1", "CF": "#404040", "OG": "#6B8E23", "PL": "#9370DB",
  "DAG": "#556B2F", "SVT": "#DDA0DD", "CGR": "#708090",
};

function colorHex(code: string): string {
  return COLOR_MAP[code.toUpperCase()] || "#888";
}

function SingleCard({ card }: { card: ProductCard }) {
  const hasPrice = card.price !== null && card.price !== undefined;
  const specs = card.specs || {};
  const specEntries = Object.entries(specs).slice(0, 3);

  return (
    <a
      href={card.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block w-[220px] shrink-0 rounded-xl overflow-hidden border border-white/10 bg-dark-800 hover:border-brand-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-brand-500/10"
    >
      {/* Image / Brand area */}
      <div className="relative h-[130px] bg-gradient-to-br from-dark-700 via-dark-800 to-dark-900 flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_40%,rgba(196,167,125,0.08),transparent_60%)]" />
        <div className="flex flex-col items-center gap-1.5 z-10">
          <div className="w-12 h-12 rounded-full bg-brand-500/15 flex items-center justify-center group-hover:bg-brand-500/25 transition-colors">
            <Guitar size={24} className="text-brand-400" />
          </div>
          <span className="text-[10px] font-medium text-brand-400/70 uppercase tracking-wider">
            {card.brand}
          </span>
        </div>
        {/* Category badge */}
        <div className="absolute top-2 left-2">
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-white/10 text-white/50 font-medium">
            {card.category}
          </span>
        </div>
        {/* Price badge */}
        {hasPrice && (
          <div className="absolute top-2 right-2">
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 font-semibold">
              ${card.price}
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-3 space-y-2">
        {/* Model name */}
        <div>
          <h4 className="text-xs font-bold text-white truncate">{card.model}</h4>
          <p className="text-[10px] text-dark-300 leading-tight mt-0.5 line-clamp-2">
            {card.name}
          </p>
        </div>

        {/* Specs */}
        {specEntries.length > 0 && (
          <div className="space-y-0.5">
            {specEntries.map(([k, v]) => (
              <div key={k} className="flex items-center gap-1 text-[9px]">
                <Tag size={8} className="text-dark-400 shrink-0" />
                <span className="text-dark-400 capitalize">{k.replace(/_/g, " ")}:</span>
                <span className="text-dark-200 truncate">{v}</span>
              </div>
            ))}
          </div>
        )}

        {/* Colors */}
        {card.colors.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            {card.colors.slice(0, 8).map((c) => (
              <span
                key={c}
                title={c}
                className="w-3 h-3 rounded-full border border-white/20 shrink-0"
                style={{ backgroundColor: colorHex(c) }}
              />
            ))}
            {card.colors.length > 8 && (
              <span className="text-[9px] text-dark-400">+{card.colors.length - 8}</span>
            )}
          </div>
        )}

        {/* CTA button */}
        <div className="pt-1">
          <span className="flex items-center justify-center gap-1 w-full py-1.5 rounded-lg bg-brand-500/15 text-brand-400 text-[10px] font-semibold group-hover:bg-brand-500/25 transition-colors">
            View Product <ExternalLink size={10} />
          </span>
        </div>
      </div>
    </a>
  );
}

export default function ProductCards({ items }: { items: ProductCard[] }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="flex animate-fade-in-up justify-start">
      <div className="w-8 mr-2 shrink-0" /> {/* Avatar spacer */}
      <div className="overflow-x-auto scrollbar-thin max-w-[calc(100%-2.5rem)]">
        <div className="flex gap-2 pb-1">
          {items.map((card) => (
            <SingleCard key={card.model} card={card} />
          ))}
        </div>
      </div>
    </div>
  );
}
