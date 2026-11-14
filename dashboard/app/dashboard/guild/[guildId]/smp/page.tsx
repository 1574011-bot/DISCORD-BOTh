/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║                                                                  ║
 * ║   UND — All In One                                               ║
 * ║                                                                  ║
 * ║                                                                  ║
 * ║   © 2026 KURAPIKA — All Rights Reserved                          ║
 * ║   Built & owned by Kurapika                                      ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */

"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Gamepad2, RefreshCw, Save, Users } from "lucide-react";
import { api } from "@/lib/api";

const inputClass =
  "w-full bg-slate-800/40 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder:text-slate-500 focus:outline-none focus:border-primary/60";

export default function SmpPage({ params }: { params: { guildId: string } }) {
  const guildId = params.guildId;

  const [config, setConfig] = useState<any>(null);
  const [channels, setChannels] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [links, setLinks] = useState<any[]>([]);
  const [form, setForm] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [cfg, chans, rls, apps, lks] = await Promise.all([
        api.getSmp(guildId),
        api.getChannels(guildId).catch(() => []),
        api.getRoles(guildId).catch(() => []),
        api.getSmpApplications(guildId).catch(() => []),
        api.getSmpLinks(guildId).catch(() => []),
      ]);

      setConfig(cfg);
      setChannels(chans || []);
      setRoles(rls || []);
      setApplications(apps || []);
      setLinks(lks || []);
      setForm({
        host: cfg?.host || "",
        port: cfg?.port ? String(cfg.port) : "",
        apply_channel_id: cfg?.apply_channel_id || "",
        review_channel_id: cfg?.review_channel_id || "",
        audit_channel_id: cfg?.audit_channel_id || "",
        member_role_id: cfg?.member_role_id || "",
        staff_role_id: cfg?.staff_role_id || "",
      });
    } catch (error: any) {
      setNotice(error?.message || "Failed to load SMP settings.");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    load();
  }, [load]);

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  async function save() {
    setSaving(true);
    setNotice(null);
    try {
      await api.updateSmp(guildId, {
        host: form.host || null,
        port: form.port ? Number(form.port) : 0,
        apply_channel_id: form.apply_channel_id || null,
        review_channel_id: form.review_channel_id || null,
        audit_channel_id: form.audit_channel_id || null,
        member_role_id: form.member_role_id || null,
        staff_role_id: form.staff_role_id || null,
      });
      setNotice("Saved.");
      await load();
    } catch (error: any) {
      setNotice(error?.message || "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  const status = config?.status;
  const online = Boolean(status?.online);

  if (loading) {
    return <div className="h-96 w-full animate-pulse bg-slate-800/20 rounded-3xl" />;
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Gamepad2 className="h-6 w-6 text-primary" />
            Minecraft SMP
          </h2>
          <p className="text-slate-400 mt-1">
            Applications, cracked-friendly IGN linking and live server status for your SMP.
          </p>
        </div>
        <button
          onClick={load}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-primary/60 hover:text-white transition"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {/* Live status */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Server</p>
            <p className="text-lg font-semibold text-white">
              {config?.host ? `${config.host}${config?.port ? `:${config.port}` : ""}` : "Not configured"}
            </p>
          </div>
          <span
            className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm ${
              online ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
            }`}
          >
            <span className={`h-2 w-2 rounded-full ${online ? "bg-emerald-400" : "bg-red-400"}`} />
            {online ? "Online" : "Offline"}
          </span>
        </div>

        {online && (
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-slate-500">Players</p>
              <p className="text-white font-semibold">
                {status.players_online} / {status.players_max}
              </p>
            </div>
            <div>
              <p className="text-slate-500">Version</p>
              <p className="text-white font-semibold">{status.version}</p>
            </div>
            <div>
              <p className="text-slate-500">Type</p>
              <p className="text-white font-semibold capitalize">{status.type || "java"}</p>
            </div>
            <div>
              <p className="text-slate-500">MOTD</p>
              <p className="text-white font-semibold truncate">{status.motd}</p>
            </div>
          </div>
        )}
      </div>

      {/* Settings */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 space-y-5">
        <h3 className="text-lg font-semibold text-white">Settings</h3>

        <div className="grid md:grid-cols-2 gap-5">
          <label className="space-y-2 text-sm text-slate-300">
            Server address
            <input
              className={inputClass}
              value={form.host || ""}
              onChange={(event) => update("host", event.target.value)}
              placeholder="play.example.com"
            />
          </label>
          <label className="space-y-2 text-sm text-slate-300">
            Port (leave empty for SRV / 25565)
            <input
              className={inputClass}
              value={form.port || ""}
              onChange={(event) => update("port", event.target.value.replace(/[^0-9]/g, ""))}
              placeholder="25565"
            />
          </label>

          {[
            { key: "apply_channel_id", label: "Apply channel" },
            { key: "review_channel_id", label: "Staff review channel" },
            { key: "audit_channel_id", label: "Audit log channel" },
          ].map((field) => (
            <label key={field.key} className="space-y-2 text-sm text-slate-300">
              {field.label}
              <select
                className={inputClass}
                value={form[field.key] || ""}
                onChange={(event) => update(field.key, event.target.value)}
              >
                <option value="">None</option>
                {channels.map((channel: any) => (
                  <option key={channel.id} value={channel.id}>
                    #{channel.name}
                  </option>
                ))}
              </select>
            </label>
          ))}

          {[
            { key: "member_role_id", label: "Member role (granted on approval)" },
            { key: "staff_role_id", label: "Staff role (can review)" },
          ].map((field) => (
            <label key={field.key} className="space-y-2 text-sm text-slate-300">
              {field.label}
              <select
                className={inputClass}
                value={form[field.key] || ""}
                onChange={(event) => update(field.key, event.target.value)}
              >
                <option value="">None</option>
                {roles.map((role: any) => (
                  <option key={role.id} value={role.id}>
                    {role.name}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={save}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition"
          >
            <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save changes"}
          </button>
          {notice && <p className="text-sm text-slate-400">{notice}</p>}
        </div>
      </div>

      {/* Applications */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" /> Applications
        </h3>
        {applications.length === 0 ? (
          <p className="text-slate-500 text-sm mt-3">No applications yet.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-slate-500 uppercase text-xs">
                <tr>
                  <th className="py-2 pr-4">IGN</th>
                  <th className="py-2 pr-4">User</th>
                  <th className="py-2 pr-4">Platform</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2">Date</th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                {applications.map((application) => (
                  <tr key={application.id} className="border-t border-slate-800">
                    <td className="py-2 pr-4 text-white font-medium">{application.ign}</td>
                    <td className="py-2 pr-4">@{application.user_id}</td>
                    <td className="py-2 pr-4 capitalize">{application.platform || "java"}</td>
                    <td className="py-2 pr-4 capitalize">{application.status}</td>
                    <td className="py-2">{(application.created_at || "").slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Linked accounts */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="text-lg font-semibold text-white">Linked accounts</h3>
        {links.length === 0 ? (
          <p className="text-slate-500 text-sm mt-3">No linked accounts yet.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-slate-500 uppercase text-xs">
                <tr>
                  <th className="py-2 pr-4">IGN</th>
                  <th className="py-2 pr-4">UUID</th>
                  <th className="py-2 pr-4">Platform</th>
                  <th className="py-2">Status</th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                {links.map((link) => (
                  <tr key={`${link.user_id}-${link.ign}`} className="border-t border-slate-800">
                    <td className="py-2 pr-4 text-white font-medium">{link.ign}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{link.uuid || "—"}</td>
                    <td className="py-2 pr-4 capitalize">{link.platform || "java"}</td>
                    <td className="py-2 capitalize">{link.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
