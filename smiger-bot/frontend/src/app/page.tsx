"use client";

import ChatWidget from "@/components/chat/ChatWidget";
import LangToggle from "@/components/LangToggle";
import { useLocale } from "@/lib/i18n";
import { Guitar, Headphones, Clock, Zap, Mail, Phone, MapPin } from "lucide-react";

export default function Home() {
  const { t } = useLocale();

  return (
    <main className="min-h-screen bg-dark-950 text-white font-display">
      {/* ── Nav ── */}
      <nav className="fixed top-0 inset-x-0 z-40 bg-dark-950/80 backdrop-blur-lg border-b border-white/5">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-500 rounded-lg flex items-center justify-center">
              <Guitar size={18} className="text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">SMIGER</span>
          </div>
          <div className="flex items-center gap-4">
            <LangToggle className="bg-white/5 border-white/10 text-white/70 hover:bg-white/10" />
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative pt-32 pb-24 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-brand-700/20 via-dark-950 to-dark-950" />
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-brand-500/10 rounded-full blur-[120px]" />

        <div className="relative max-w-4xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-medium mb-8">
            <span className="w-2 h-2 bg-brand-400 rounded-full animate-pulse" />
            {t.chat.headerStatus}
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-tight mb-6">
            {t.landing.title.split(" ").map((word, i) => (
              <span key={i} className={i === 0 ? "text-gradient" : ""}>
                {word}{" "}
              </span>
            ))}
          </h1>

          <p className="text-lg text-dark-300 max-w-2xl mx-auto mb-10 leading-relaxed">
            {t.landing.subtitle}
          </p>

          <p className="text-sm text-dark-400">{t.landing.chatHint}</p>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="py-20 border-t border-white/5">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: Guitar, title: t.landing.feature1Title, desc: t.landing.feature1Desc },
              { icon: Zap, title: t.landing.feature2Title, desc: t.landing.feature2Desc },
              { icon: Clock, title: t.landing.feature3Title, desc: t.landing.feature3Desc },
            ].map(({ icon: Icon, title, desc }, i) => (
              <div
                key={i}
                className="group bg-dark-900/50 border border-white/5 rounded-2xl p-7 hover:border-brand-500/30 hover:bg-dark-900 transition-all duration-300"
              >
                <div className="w-12 h-12 bg-brand-500/10 rounded-xl flex items-center justify-center mb-5 group-hover:bg-brand-500/20 transition-colors">
                  <Icon size={22} className="text-brand-400" />
                </div>
                <h3 className="font-semibold text-white mb-2 text-lg">{title}</h3>
                <p className="text-sm text-dark-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── About ── */}
      <section className="py-20 border-t border-white/5 bg-dark-900/30">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold mb-4">
                Creating Joy<br />
                <span className="text-gradient">for Everyone</span>
              </h2>
              <p className="text-dark-300 leading-relaxed mb-6">
                Smiger Guitars is a brand under Vines Music. With over 15 years of experience, 
                a self-built factory spanning 10,000m², 6 production lines, and 10+ R&amp;D experts, 
                we craft premium musical instruments for the world.
              </p>
              <div className="flex flex-wrap gap-6 text-sm text-dark-400">
                <div><span className="text-2xl font-bold text-brand-400 block">15+</span>Years</div>
                <div><span className="text-2xl font-bold text-brand-400 block">10K</span>m² Factory</div>
                <div><span className="text-2xl font-bold text-brand-400 block">6</span>Prod. Lines</div>
                <div><span className="text-2xl font-bold text-brand-400 block">50+</span>Countries</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[Headphones, Guitar, Zap, Clock].map((Icon, i) => (
                <div key={i} className="bg-dark-800 border border-white/5 rounded-xl p-6 flex flex-col items-center justify-center gap-3 aspect-square">
                  <Icon size={28} className="text-brand-400/60" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-12 border-t border-white/5">
        <div className="max-w-5xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-start gap-8">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
                  <Guitar size={16} className="text-white" />
                </div>
                <span className="font-bold">SMIGER</span>
              </div>
              <p className="text-sm text-dark-400 max-w-xs">Creating Joy for Everyone</p>
            </div>
            <div className="flex flex-col gap-2 text-sm text-dark-400">
              <div className="flex items-center gap-2"><Mail size={14} className="text-brand-400" /> info@vinesmusic.com</div>
              <div className="flex items-center gap-2"><Phone size={14} className="text-brand-400" /> +86 13826092986</div>
              <div className="flex items-center gap-2"><MapPin size={14} className="text-brand-400" /> Guangzhou, China</div>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-white/5 text-xs text-dark-500 text-center">
            © 2026 Smiger Guitar — All Rights Reserved. Powered by AI-OS.
          </div>
        </div>
      </footer>

      <ChatWidget />
    </main>
  );
}
