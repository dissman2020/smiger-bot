"use client";

import { useEffect, useMemo, useState } from "react";
import { Save, Zap, CheckCircle, XCircle, MessageCircle, Send, MessagesSquare } from "lucide-react";
import { getApiSettings, updateApiSettings, testApiConnections } from "@/lib/api";
import { useLocale } from "@/lib/i18n";

type TelegramAccount = {
  name: string;
  enabled: boolean;
  bot_token: string;
  admin_chat_id: string;
  webhook_secret: string;
};

export default function SettingsPage() {
  const { t } = useLocale();
  const [form, setForm] = useState({
    llm_api_key: "",
    llm_base_url: "",
    llm_model: "",
    embedding_url: "",
    embedding_easyllm_id: "",
    embedding_dimensions: 1024,
    whatsapp_enabled: false,
    whatsapp_phone_number_id: "",
    whatsapp_access_token: "",
    whatsapp_verify_token: "",
    whatsapp_admin_phone: "",
    whatsapp_template_name: "",
    telegram_enabled: false,
    telegram_active_account: "",
    telegram_accounts: [] as TelegramAccount[],
    gchat_enabled: false,
    gchat_webhook_url: "",
    gchat_verify_token: "",
  });

  const [tgDraft, setTgDraft] = useState<TelegramAccount>({
    name: "Tele1",
    enabled: true,
    bot_token: "",
    admin_chat_id: "",
    webhook_secret: "",
  });
  const [editingTgName, setEditingTgName] = useState("");

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [telegramSaving, setTelegramSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [testResult, setTestResult] = useState<any>(null);

  const activeTelegram = useMemo(
    () => form.telegram_accounts.find((a) => a.name === form.telegram_active_account),
    [form.telegram_accounts, form.telegram_active_account]
  );

  useEffect(() => {
    getApiSettings()
      .then((data) => {
        setForm((f) => ({
          ...f,
          llm_base_url: data.llm_base_url,
          llm_model: data.llm_model,
          embedding_url: data.embedding_url,
          embedding_easyllm_id: data.embedding_easyllm_id,
          embedding_dimensions: data.embedding_dimensions,
          whatsapp_enabled: data.whatsapp_enabled || false,
          whatsapp_phone_number_id: data.whatsapp_phone_number_id || "",
          whatsapp_verify_token: data.whatsapp_verify_token || "",
          whatsapp_admin_phone: data.whatsapp_admin_phone || "",
          whatsapp_template_name: data.whatsapp_template_name || "",
          telegram_enabled: data.telegram_enabled || false,
          telegram_active_account: data.telegram_active_account || "",
          telegram_accounts: ((data.telegram_accounts || []) as TelegramAccount[]).map((a) => ({
            ...a,
            enabled: a.enabled !== false,
          })),
          gchat_enabled: data.gchat_enabled || false,
          gchat_webhook_url: data.gchat_webhook_url || "",
          gchat_verify_token: data.gchat_verify_token || "",
        }));
      })
      .catch(console.error);
  }, []);

  const inputCls =
    "w-full bg-dark-800 text-white placeholder:text-dark-500 rounded-lg border border-white/10 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50";

  const persistTelegram = async (
    accounts: TelegramAccount[],
    activeAccount: string,
    successMsg: string
  ) => {
    setTelegramSaving(true);
    setMessage("");
    try {
      const payload = {
        telegram_enabled: form.telegram_enabled,
        telegram_accounts: accounts,
        telegram_active_account: activeAccount,
      };
      const updated = await updateApiSettings(payload);
      setForm((prev) => ({
        ...prev,
        telegram_enabled: updated.telegram_enabled || false,
        telegram_accounts: (updated.telegram_accounts || []) as TelegramAccount[],
        telegram_active_account: updated.telegram_active_account || "",
      }));
      setMessage(successMsg);
    } catch (e: any) {
      setMessage(e.message || "Telegram 保存失败");
    } finally {
      setTelegramSaving(false);
    }
  };

  const handleSaveTelegramAccount = async () => {
    const name = tgDraft.name.trim();
    const token = tgDraft.bot_token.trim();
    const chatId = tgDraft.admin_chat_id.trim();
    if (!name) {
      setMessage("请填写账号名称，例如 Tele1 或 Tele2");
      return;
    }
    if (!token) {
      setMessage("请填写 Bot Token");
      return;
    }
    if (!chatId) {
      setMessage("请填写管理员 Chat ID");
      return;
    }

    const cleaned: TelegramAccount = {
      name,
      enabled: tgDraft.enabled !== false,
      bot_token: token,
      admin_chat_id: chatId,
      webhook_secret: tgDraft.webhook_secret.trim(),
    };

    const idx = form.telegram_accounts.findIndex((a) => a.name === name);
    const nextAccounts = [...form.telegram_accounts];
    if (idx >= 0) {
      nextAccounts[idx] = cleaned;
    } else {
      nextAccounts.push(cleaned);
    }

    const nextActive = form.telegram_active_account || name;
    await persistTelegram(nextAccounts, nextActive, `账号 ${name} 已保存`);
    setEditingTgName("");
  };

  const handleEditTelegramAccount = (name: string) => {
    const account = form.telegram_accounts.find((a) => a.name === name);
    if (!account) return;
    setTgDraft({ ...account });
    setEditingTgName(name);
    setMessage(`正在编辑 ${name}`);
  };

  const handleSwitchTelegramAccount = async (name: string) => {
    if (name === form.telegram_active_account) return;
    await persistTelegram(form.telegram_accounts, name, `已切换到 ${name}`);
  };

  const handleDeleteTelegramAccount = async (name: string) => {
    const nextAccounts = form.telegram_accounts.filter((a) => a.name !== name);
    const nextActive =
      form.telegram_active_account === name ? (nextAccounts[0]?.name || "") : form.telegram_active_account;
    await persistTelegram(nextAccounts, nextActive, `账号 ${name} 已删除`);
    if (editingTgName === name) {
      setEditingTgName("");
      setTgDraft({ name: "Tele1", enabled: true, bot_token: "", admin_chat_id: "", webhook_secret: "" });
    }
  };

  const handleToggleTelegramEnabled = async (name: string) => {
    const nextAccounts = form.telegram_accounts.map((a) =>
      a.name === name ? { ...a, enabled: !a.enabled } : a
    );
    await persistTelegram(nextAccounts, form.telegram_active_account, `账号 ${name} 启用状态已更新`);
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      const payload: any = { ...form };
      if (!payload.llm_api_key) delete payload.llm_api_key;
      if (!payload.whatsapp_access_token) delete payload.whatsapp_access_token;
      await updateApiSettings(payload);
      setMessage(t.settingsPage.saved);
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await testApiConnections();
      setTestResult(r);
    } catch (e: any) {
      setTestResult({
        llm_ok: false,
        llm_message: e.message,
        embedding_ok: false,
        embedding_message: e.message,
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-6">{t.settingsPage.title}</h1>

      <div className="space-y-6">
        <div className="bg-dark-900 border border-white/5 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">{t.settingsPage.llmSection}</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-dark-300 mb-1">{t.settingsPage.apiKey}</label>
              <input
                type="password"
                value={form.llm_api_key}
                onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })}
                placeholder="••••••••"
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-sm text-dark-300 mb-1">{t.settingsPage.baseUrl}</label>
              <input
                type="text"
                value={form.llm_base_url}
                onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-sm text-dark-300 mb-1">{t.settingsPage.model}</label>
              <input
                type="text"
                value={form.llm_model}
                onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                className={inputCls}
              />
            </div>
          </div>
        </div>

        <div className="bg-dark-900 border border-white/5 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">{t.settingsPage.embeddingSection}</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-dark-300 mb-1">{t.settingsPage.embeddingUrl}</label>
              <input
                type="text"
                value={form.embedding_url}
                onChange={(e) => setForm({ ...form, embedding_url: e.target.value })}
                className={inputCls}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-dark-300 mb-1">{t.settingsPage.easyllmId}</label>
                <input
                  type="text"
                  value={form.embedding_easyllm_id}
                  onChange={(e) => setForm({ ...form, embedding_easyllm_id: e.target.value })}
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">{t.settingsPage.dimensions}</label>
                <input
                  type="number"
                  value={form.embedding_dimensions}
                  onChange={(e) => setForm({ ...form, embedding_dimensions: parseInt(e.target.value, 10) || 1024 })}
                  className={inputCls}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-dark-900 border border-white/5 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <MessageCircle size={20} className="text-emerald-400" />
              {(t as any).settingsPage?.whatsappSection ?? "WhatsApp 通道"}
            </h2>
            <button
              type="button"
              onClick={() => setForm({ ...form, whatsapp_enabled: !form.whatsapp_enabled })}
              className={`relative w-11 h-6 rounded-full transition-colors ${form.whatsapp_enabled ? "bg-emerald-500" : "bg-dark-600"}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${form.whatsapp_enabled ? "translate-x-5" : ""}`} />
            </button>
          </div>
          {form.whatsapp_enabled && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-dark-300 mb-1">Phone Number ID</label>
                <input
                  type="text"
                  value={form.whatsapp_phone_number_id}
                  onChange={(e) => setForm({ ...form, whatsapp_phone_number_id: e.target.value })}
                  placeholder="Meta 分配的号码 ID"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Access Token</label>
                <input
                  type="password"
                  value={form.whatsapp_access_token}
                  onChange={(e) => setForm({ ...form, whatsapp_access_token: e.target.value })}
                  placeholder="••••••••"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Webhook Verify Token</label>
                <input
                  type="text"
                  value={form.whatsapp_verify_token}
                  onChange={(e) => setForm({ ...form, whatsapp_verify_token: e.target.value })}
                  placeholder="自定义随机字符串"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">{(t as any).settingsPage?.whatsappAdminPhone ?? "管理员 WhatsApp 号码"}</label>
                <input
                  type="text"
                  value={form.whatsapp_admin_phone}
                  onChange={(e) => setForm({ ...form, whatsapp_admin_phone: e.target.value })}
                  placeholder="+8613812345678"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">{(t as any).settingsPage?.whatsappTemplate ?? "模板名称（可选）"}</label>
                <input
                  type="text"
                  value={form.whatsapp_template_name}
                  onChange={(e) => setForm({ ...form, whatsapp_template_name: e.target.value })}
                  placeholder="new_customer_inquiry"
                  className={inputCls}
                />
              </div>
            </div>
          )}
        </div>

        <div className="bg-dark-900 border border-white/5 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Send size={20} className="text-sky-400" />
              Telegram 通道
            </h2>
            <button
              type="button"
              onClick={() => setForm({ ...form, telegram_enabled: !form.telegram_enabled })}
              className={`relative w-11 h-6 rounded-full transition-colors ${form.telegram_enabled ? "bg-sky-500" : "bg-dark-600"}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${form.telegram_enabled ? "translate-x-5" : ""}`} />
            </button>
          </div>
          {form.telegram_enabled && (
            <div className="space-y-4">
              <div className="bg-dark-800/50 rounded-lg p-3 border border-white/5">
                <p className="text-xs text-dark-300">当前账号: <span className="text-sky-400 font-medium">{form.telegram_active_account || "未设置"}</span></p>
                <p className="text-xs text-dark-500 mt-1">
                  可直接保存为 Tele1 / Tele2，然后点击切换按钮立即生效。
                </p>
              </div>

              <div className="grid grid-cols-1 gap-3">
                <div>
                  <label className="block text-sm text-dark-300 mb-1">账号名称</label>
                  <input
                    type="text"
                    value={tgDraft.name}
                    onChange={(e) => setTgDraft({ ...tgDraft, name: e.target.value })}
                    placeholder="Tele1"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="block text-sm text-dark-300 mb-1">Bot Token</label>
                  <input
                    type="password"
                    value={tgDraft.bot_token}
                    onChange={(e) => setTgDraft({ ...tgDraft, bot_token: e.target.value })}
                    placeholder="123456:AA..."
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="block text-sm text-dark-300 mb-1">管理员 Chat ID</label>
                  <input
                    type="text"
                    value={tgDraft.admin_chat_id}
                    onChange={(e) => setTgDraft({ ...tgDraft, admin_chat_id: e.target.value })}
                    placeholder="8432959658"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="block text-sm text-dark-300 mb-1">Webhook Secret（可选）</label>
                  <input
                    type="text"
                    value={tgDraft.webhook_secret}
                    onChange={(e) => setTgDraft({ ...tgDraft, webhook_secret: e.target.value })}
                    placeholder="optional-secret"
                    className={inputCls}
                  />
                </div>
                <label className="flex items-center gap-2 text-sm text-dark-300">
                  <input
                    type="checkbox"
                    checked={tgDraft.enabled}
                    onChange={(e) => setTgDraft({ ...tgDraft, enabled: e.target.checked })}
                  />
                  启用此账号
                </label>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveTelegramAccount}
                  disabled={telegramSaving}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-sky-500 text-white text-sm font-medium rounded-lg hover:bg-sky-600 disabled:opacity-50 transition-colors"
                >
                  {telegramSaving ? "保存中..." : editingTgName ? `更新 ${editingTgName}` : "保存账号"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditingTgName("");
                    setTgDraft({
                      name: `Tele${form.telegram_accounts.length + 1}`,
                      enabled: true,
                      bot_token: "",
                      admin_chat_id: "",
                      webhook_secret: "",
                    });
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-dark-800 border border-white/10 text-dark-200 text-sm rounded-lg hover:bg-dark-700 transition-colors"
                >
                  新建账号
                </button>
              </div>

              {form.telegram_accounts.length > 0 && (
                <div className="space-y-2">
                  {form.telegram_accounts.map((acc) => {
                    const isActive = form.telegram_active_account === acc.name;
                    return (
                      <div key={acc.name} className="bg-dark-800/60 border border-white/10 rounded-lg p-3 flex flex-col gap-2">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm text-white font-medium">{acc.name}</p>
                            <p className="text-xs text-dark-400">Chat ID: {acc.admin_chat_id || "-"}</p>
                          </div>
                          <span className={`text-xs px-2 py-1 rounded-full ${isActive ? "bg-sky-500/20 text-sky-300 border border-sky-400/30" : "bg-dark-700 text-dark-300 border border-white/10"}`}>
                            {isActive ? "当前账号" : "备用账号"}
                          </span>
                        </div>
                        <p className="text-xs text-dark-500">
                          状态: {acc.enabled ? "已启用" : "已停用"}
                        </p>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleSwitchTelegramAccount(acc.name)}
                            disabled={telegramSaving || isActive || !acc.enabled}
                            className="px-3 py-1.5 text-xs rounded-md bg-sky-500 text-white disabled:opacity-40 hover:bg-sky-600 transition-colors"
                          >
                            切换
                          </button>
                          <button
                            type="button"
                            onClick={() => handleEditTelegramAccount(acc.name)}
                            className="px-3 py-1.5 text-xs rounded-md bg-dark-700 text-dark-200 hover:bg-dark-600 transition-colors"
                          >
                            编辑
                          </button>
                          <button
                            type="button"
                            onClick={() => handleToggleTelegramEnabled(acc.name)}
                            disabled={telegramSaving}
                            className="px-3 py-1.5 text-xs rounded-md bg-indigo-600/80 text-white hover:bg-indigo-600 disabled:opacity-40 transition-colors"
                          >
                            {acc.enabled ? "停用" : "启用"}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteTelegramAccount(acc.name)}
                            disabled={telegramSaving}
                            className="px-3 py-1.5 text-xs rounded-md bg-red-600/80 text-white hover:bg-red-600 disabled:opacity-40 transition-colors"
                          >
                            删除
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              <div className="bg-dark-800/60 rounded-lg p-3 border border-white/5">
                <p className="text-xs text-dark-400">
                  <span className="text-dark-300 font-medium">Webhook URL: </span>
                  <code className="text-sky-400">https://{"{your-domain}"}/api/webhook/telegram</code>
                </p>
              </div>

              {activeTelegram && (
                <div className="text-xs text-dark-500">
                  激活账号已绑定 Chat ID: <span className="text-dark-300">{activeTelegram.admin_chat_id}</span>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="bg-dark-900 border border-white/5 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <MessagesSquare size={20} className="text-yellow-400" />
              Google Chat 通道
            </h2>
            <button
              type="button"
              onClick={() => setForm({ ...form, gchat_enabled: !form.gchat_enabled })}
              className={`relative w-11 h-6 rounded-full transition-colors ${form.gchat_enabled ? "bg-yellow-500" : "bg-dark-600"}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${form.gchat_enabled ? "translate-x-5" : ""}`} />
            </button>
          </div>
          {form.gchat_enabled && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-dark-300 mb-1">Webhook URL</label>
                <input
                  type="text"
                  value={form.gchat_webhook_url}
                  onChange={(e) => setForm({ ...form, gchat_webhook_url: e.target.value })}
                  placeholder="https://chat.googleapis.com/v1/spaces/..."
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Verify Token（可选）</label>
                <input
                  type="text"
                  value={form.gchat_verify_token}
                  onChange={(e) => setForm({ ...form, gchat_verify_token: e.target.value })}
                  placeholder="random-token"
                  className={inputCls}
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-brand-500 text-white text-sm font-medium rounded-lg hover:bg-brand-600 disabled:opacity-50 transition-colors"
          >
            <Save size={16} />
            {saving ? t.settingsPage.saving : t.settingsPage.save}
          </button>
          <button
            onClick={handleTest}
            disabled={testing}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-dark-800 border border-white/10 text-dark-300 text-sm font-medium rounded-lg hover:bg-dark-700 disabled:opacity-50 transition-colors"
          >
            <Zap size={16} />
            {testing ? t.settingsPage.testing : t.settingsPage.test}
          </button>
        </div>

        {message && <p className="text-sm text-brand-400">{message}</p>}

        {testResult && (
          <div className="bg-dark-900 border border-white/5 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2">
              {testResult.llm_ok ? <CheckCircle size={16} className="text-green-400" /> : <XCircle size={16} className="text-red-400" />}
              <span className="text-sm text-dark-200">LLM: {testResult.llm_ok ? t.settingsPage.connected : t.settingsPage.failed}</span>
              {!testResult.llm_ok && <span className="text-xs text-dark-500 ml-2">{testResult.llm_message}</span>}
            </div>
            <div className="flex items-center gap-2">
              {testResult.embedding_ok ? <CheckCircle size={16} className="text-green-400" /> : <XCircle size={16} className="text-red-400" />}
              <span className="text-sm text-dark-200">Embedding: {testResult.embedding_ok ? t.settingsPage.connected : t.settingsPage.failed}</span>
              {!testResult.embedding_ok && <span className="text-xs text-dark-500 ml-2">{testResult.embedding_message}</span>}
            </div>
            {form.whatsapp_enabled && (
              <div className="flex items-center gap-2">
                {testResult.whatsapp_ok ? <CheckCircle size={16} className="text-green-400" /> : <XCircle size={16} className="text-red-400" />}
                <span className="text-sm text-dark-200">WhatsApp: {testResult.whatsapp_ok ? t.settingsPage.connected : t.settingsPage.failed}</span>
                {!testResult.whatsapp_ok && <span className="text-xs text-dark-500 ml-2">{testResult.whatsapp_message}</span>}
              </div>
            )}
            {form.telegram_enabled && (
              <div className="flex items-center gap-2">
                {testResult.telegram_ok ? <CheckCircle size={16} className="text-green-400" /> : <XCircle size={16} className="text-red-400" />}
                <span className="text-sm text-dark-200">Telegram: {testResult.telegram_ok ? t.settingsPage.connected : t.settingsPage.failed}</span>
                {!testResult.telegram_ok && <span className="text-xs text-dark-500 ml-2">{testResult.telegram_message}</span>}
              </div>
            )}
            {form.gchat_enabled && (
              <div className="flex items-center gap-2">
                {testResult.gchat_ok ? <CheckCircle size={16} className="text-green-400" /> : <XCircle size={16} className="text-red-400" />}
                <span className="text-sm text-dark-200">Google Chat: {testResult.gchat_ok ? t.settingsPage.connected : t.settingsPage.failed}</span>
                {!testResult.gchat_ok && <span className="text-xs text-dark-500 ml-2">{testResult.gchat_message}</span>}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
