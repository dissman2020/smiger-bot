"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { BarChart3, BookOpen, HelpCircle, LogOut, MessageSquare, Users, Guitar, Settings, Headphones, Phone, Send } from "lucide-react";
import clsx from "clsx";
import { useLocale } from "@/lib/i18n";
import { getHandoffCount } from "@/lib/api";
import LangToggle from "@/components/LangToggle";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useLocale();
  const [handoffPending, setHandoffPending] = useState(0);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const data = await getHandoffCount();
        if (mounted) setHandoffPending(data.pending + data.active);
      } catch { /* ignore */ }
    };
    poll();
    const iv = setInterval(poll, 5000);
    return () => { mounted = false; clearInterval(iv); };
  }, []);

  const links = [
    { href: "/admin", label: t.admin.dashboard, icon: BarChart3 },
    { href: "/admin/handoff", label: (t.admin as any).handoff ?? "人工接管", icon: Phone, badge: handoffPending },
    { href: "/admin/telegram-support", label: "Telegram Support", icon: Send },
    { href: "/admin/knowledge", label: t.admin.knowledgeBase, icon: BookOpen },
    { href: "/admin/conversations", label: t.admin.conversations, icon: MessageSquare },
    { href: "/admin/leads", label: t.admin.leads, icon: Users },
    { href: "/admin/faq", label: (t.admin as any).faq ?? "FAQ", icon: HelpCircle },
    { href: "/admin/cs-data", label: t.admin.csData ?? "CS Data", icon: Headphones },
    { href: "/admin/settings", label: t.admin.settings ?? "API Settings", icon: Settings },
  ];

  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    router.push("/admin/login");
  };

  return (
    <aside className="w-60 bg-dark-900 border-r border-white/5 flex flex-col h-screen sticky top-0">
      <div className="p-5 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
            <Guitar size={16} className="text-white" />
          </div>
          <span className="font-bold text-white text-sm">{t.admin.brand}</span>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {links.map(({ href, label, icon: Icon, badge }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                active ? "bg-brand-500/15 text-brand-400 font-medium" : "text-dark-400 hover:bg-white/5 hover:text-dark-200"
              )}
            >
              <Icon size={18} />
              <span className="flex-1">{label}</span>
              {badge != null && badge > 0 && (
                <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                  {badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 space-y-2 border-t border-white/5">
        <div className="px-3 py-1">
          <LangToggle className="w-full justify-center bg-white/5 border-white/10 text-dark-400 hover:bg-white/10" />
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-dark-500 hover:bg-white/5 hover:text-dark-300 w-full transition-colors"
        >
          <LogOut size={18} />
          {t.admin.signOut}
        </button>
      </div>
    </aside>
  );
}
