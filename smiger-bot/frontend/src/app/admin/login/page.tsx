"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Guitar } from "lucide-react";
import { login } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import LangToggle from "@/components/LangToggle";

export default function LoginPage() {
  const router = useRouter();
  const { t } = useLocale();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { access_token } = await login(username, password);
      localStorage.setItem("admin_token", access_token);
      router.push("/admin");
    } catch {
      setError(t.login.error);
    } finally {
      setLoading(false);
    }
  };

  const inputCls = "w-full bg-dark-800 text-white placeholder:text-dark-500 rounded-lg border border-white/10 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50";

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-950 px-4 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-brand-700/10 via-dark-950 to-dark-950" />
      <div className="absolute top-5 right-5 z-10">
        <LangToggle />
      </div>
      <div className="w-full max-w-sm relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-brand-500 rounded-2xl text-white mb-4">
            <Guitar size={28} />
          </div>
          <h1 className="text-xl font-bold text-white">{t.login.title}</h1>
          <p className="text-sm text-dark-400 mt-1">{t.login.subtitle}</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-dark-900 rounded-xl border border-white/5 p-6 space-y-4">
          {error && <div className="text-sm text-red-400 bg-red-500/10 rounded-lg p-3">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-1">{t.login.username}</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className={inputCls} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-1">{t.login.password}</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} required />
          </div>
          <button type="submit" disabled={loading} className="w-full py-2.5 bg-brand-500 text-white text-sm font-medium rounded-lg hover:bg-brand-600 disabled:opacity-50 transition-colors">
            {loading ? t.login.signingIn : t.login.signIn}
          </button>
        </form>
      </div>
    </div>
  );
}
