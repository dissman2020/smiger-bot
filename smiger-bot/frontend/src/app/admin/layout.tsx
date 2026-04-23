"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import Sidebar from "@/components/admin/Sidebar";
import { getHandoffCount } from "@/lib/api";

function HandoffToast({ count, onClose }: { count: number; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 8000);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div className="fixed top-6 right-6 z-[100] animate-fade-in-up">
      <div className="bg-amber-600 text-white px-5 py-3 rounded-xl shadow-2xl flex items-center gap-3 min-w-[280px]">
        <AlertTriangle size={20} className="shrink-0" />
        <div className="flex-1">
          <p className="font-semibold text-sm">购买意向提醒</p>
          <p className="text-xs text-white/80">有 {count} 个客户等待人工接入</p>
        </div>
        <button onClick={onClose} className="text-white/70 hover:text-white">
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [toast, setToast] = useState<number | null>(null);
  const lastPendingRef = useRef(0);
  const isLoginPage = pathname === "/admin/login";

  useEffect(() => {
    if (isLoginPage) { setReady(true); return; }
    const token = localStorage.getItem("admin_token");
    if (!token) router.replace("/admin/login");
    else setReady(true);
  }, [isLoginPage, router]);

  const dismissToast = useCallback(() => setToast(null), []);

  useEffect(() => {
    if (isLoginPage || !ready) return;
    let mounted = true;
    const poll = async () => {
      try {
        const data = await getHandoffCount();
        if (!mounted) return;
        if (data.pending > lastPendingRef.current && data.pending > 0) {
          setToast(data.pending);
        }
        lastPendingRef.current = data.pending;
      } catch { /* ignore */ }
    };
    poll();
    const iv = setInterval(poll, 5000);
    return () => { mounted = false; clearInterval(iv); };
  }, [isLoginPage, ready]);

  if (!ready) return null;
  if (isLoginPage) return <>{children}</>;

  return (
    <div className="flex min-h-screen bg-dark-950">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">{children}</main>
      {toast !== null && <HandoffToast count={toast} onClose={dismissToast} />}
    </div>
  );
}
