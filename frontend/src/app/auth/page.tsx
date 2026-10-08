"use client";

import { FormEvent, useState } from "react";
import { api, getErrorMessage } from "@/lib/api";

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true); setError(null); setMessage(null);
    try {
      const result = mode === "login" ? await api.login(email, password) : await api.register(email, password);
      localStorage.setItem("aise_access_token", result.access_token);
      setMessage(`Signed in as ${result.user.email} (${result.user.role}).`);
      const next = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("next") : null;
      if (next && next.startsWith("/")) window.location.href = next;
    } catch (reason) { setError(getErrorMessage(reason)); }
    finally { setLoading(false); }
  };

  return (
    <div className="max-w-xl mx-auto px-6 py-10">
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6">
        <h1 className="text-xl font-semibold text-slate-800">{mode === "login" ? "Sign in" : "Create your account"}</h1>
        <p className="text-sm text-slate-500 mt-1">Phase 4 access foundation. Repository permissions will be enforced next.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block text-sm text-slate-700">Email<input aria-label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg" /></label>
          <label className="block text-sm text-slate-700">Password<input aria-label="Password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg" /></label>
          <button type="submit" disabled={loading} className="w-full px-4 py-2 rounded-lg bg-sky-600 text-white text-sm disabled:opacity-50">{loading ? "Working..." : mode === "login" ? "Sign in" : "Create account"}</button>
        </form>
        {message && <p role="status" className="mt-4 text-sm text-emerald-700">{message}</p>}
        {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
        <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setMessage(null); setError(null); }} className="mt-5 text-sm text-sky-700 underline">{mode === "login" ? "Create a new account" : "Use an existing account"}</button>
      </div>
    </div>
  );
}
