"use client";

import { FormEvent, useState } from "react";
import { api, getErrorMessage, Workspace, WorkspaceInvitation, WorkspaceMember, UsageSummary } from "@/lib/api";

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState("");
  const [renameWorkspaceId, setRenameWorkspaceId] = useState<string | null>(null);
  const [invitations, setInvitations] = useState<Record<string, WorkspaceInvitation[]>>({});
  const [members, setMembers] = useState<Record<string, WorkspaceMember[]>>({});
  const [usage, setUsage] = useState<UsageSummary | null>(null);

  const loadWorkspaceAdminData = async (items: Workspace[]) => {
    const adminItems = items.filter((workspace) => workspace.role === "owner" || workspace.role === "admin");
    const results = await Promise.all(adminItems.map(async (workspace) => {
      try {
        const [workspaceInvitations, workspaceMembers] = await Promise.all([api.listWorkspaceInvitations(workspace.id), api.listWorkspaceMembers(workspace.id)]);
        return { id: workspace.id, workspaceInvitations, workspaceMembers };
      } catch { return { id: workspace.id, workspaceInvitations: [], workspaceMembers: [] }; }
    }));
    setInvitations(Object.fromEntries(results.map((item) => [item.id, item.workspaceInvitations])));
    setMembers(Object.fromEntries(results.map((item) => [item.id, item.workspaceMembers])));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true); setError(null); setMessage(null);
    try {
      const result = mode === "login" ? await api.login(email, password) : await api.register(email, password);
      localStorage.setItem("aise_access_token", result.access_token);
      setMessage(`Signed in as ${result.user.email} (${result.user.role}).`);
      const workspaceItems = await api.listWorkspaces();
      setWorkspaces(workspaceItems);
      await loadWorkspaceAdminData(workspaceItems);
      setUsage(await api.getUsage());
      const next = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("next") : null;
      if (next && next.startsWith("/")) window.location.href = next;
    } catch (reason) { setError(getErrorMessage(reason)); }
    finally { setLoading(false); }
  };

  const createInvite = async (workspace: Workspace) => {
    setError(null); setMessage(null); setGeneratedToken(null);
    try {
      const invitation = await api.createWorkspaceInvitation(workspace.id, inviteEmail.trim());
      setGeneratedToken(invitation.invite_token ?? null);
      setInviteEmail("");
      setInvitations((current) => ({ ...current, [workspace.id]: [...(current[workspace.id] ?? []), invitation] }));
      setMessage(`Invitation created for ${invitation.email}. Share the token once.`);
    } catch (reason) { setError(getErrorMessage(reason)); }
  };

  const copyInvitationToken = async () => {
    if (!generatedToken) return;
    try {
      await navigator.clipboard.writeText(generatedToken);
      setMessage("Invitation token copied. Share it only with the invited email address.");
    } catch {
      setError("Could not copy the invitation token. Select and copy it manually.");
    }
  };

  const revokeInvite = async (workspace: Workspace, invitation: WorkspaceInvitation) => {
    setError(null); setMessage(null);
    try {
      await api.revokeWorkspaceInvitation(workspace.id, invitation.id);
      setInvitations((current) => ({ ...current, [workspace.id]: (current[workspace.id] ?? []).filter((item) => item.id !== invitation.id) }));
      setMessage(`Revoked the invitation for ${invitation.email}.`);
    } catch (reason) { setError(getErrorMessage(reason)); }
  };

  const updateMember = async (workspace: Workspace, member: WorkspaceMember, role: string) => {
    setError(null); setMessage(null);
    try {
      const updated = await api.updateWorkspaceMember(workspace.id, member.user_id, role);
      setMembers((current) => ({ ...current, [workspace.id]: (current[workspace.id] ?? []).map((item) => item.user_id === updated.user_id ? updated : item) }));
      setMessage(`Updated ${updated.email} to ${updated.role}.`);
    } catch (reason) { setError(getErrorMessage(reason)); }
  };

  const removeMember = async (workspace: Workspace, member: WorkspaceMember) => {
    if (!window.confirm(`Remove ${member.email} from ${workspace.name}?`)) return;
    setError(null); setMessage(null);
    try {
      await api.removeWorkspaceMember(workspace.id, member.user_id);
      setMembers((current) => ({ ...current, [workspace.id]: (current[workspace.id] ?? []).filter((item) => item.user_id !== member.user_id) }));
      setMessage(`Removed ${member.email} from ${workspace.name}.`);
    } catch (reason) { setError(getErrorMessage(reason)); }
  };

  const acceptInvite = async () => {
    setError(null); setMessage(null);
    try {
      const workspace = await api.acceptWorkspaceInvitation(inviteToken.trim());
      setWorkspaces((current) => current.some((item) => item.id === workspace.id) ? current : [...current, workspace]);
      setMessage(`Joined ${workspace.name} as ${workspace.role}.`);
      setInviteToken("");
    } catch (reason) { setError(getErrorMessage(reason)); }
  };

  const createWorkspace = async () => {
    setError(null); setMessage(null);
    try {
      const workspace = await api.createWorkspace(workspaceName.trim());
      setWorkspaces((current) => [...current, workspace]);
      setWorkspaceName("");
      setMessage(`Created ${workspace.name}.`);
    } catch (reason) { setError(getErrorMessage(reason)); }
  };

  const renameWorkspace = async (workspace: Workspace) => {
    const name = window.prompt("New workspace name", workspace.name)?.trim();
    if (!name || name === workspace.name) return;
    setError(null); setMessage(null);
    try {
      const updated = await api.renameWorkspace(workspace.id, name);
      setWorkspaces((current) => current.map((item) => item.id === updated.id ? updated : item));
      setMessage(`Renamed workspace to ${updated.name}.`);
    } catch (reason) { setError(getErrorMessage(reason)); }
    finally { setRenameWorkspaceId(null); }
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
        {usage && <div className="mt-4 border border-slate-200 rounded-lg p-3 text-xs text-slate-600"><p className="font-semibold text-slate-700">AI usage today</p><p className="mt-1">{usage.used} used · {usage.remaining === null ? "unlimited" : `${usage.remaining} remaining`} of {usage.daily_limit === 0 ? "unlimited" : usage.daily_limit}</p></div>}
        {workspaces.length > 0 && <div className="mt-4 border border-slate-200 rounded-lg p-3"><p className="text-xs font-semibold text-slate-700">Your workspaces</p>{workspaces.map((workspace) => <div key={workspace.id} className="mt-2"><div className="flex items-center justify-between"><p className="text-xs text-slate-600">{workspace.name} · {workspace.role}</p>{(workspace.role === "owner" || workspace.role === "admin") && <button type="button" onClick={() => { setRenameWorkspaceId(workspace.id); void renameWorkspace(workspace); }} className="text-xs text-sky-700 underline">{renameWorkspaceId === workspace.id ? "Renaming..." : "Rename"}</button>}</div>{(workspace.role === "owner" || workspace.role === "admin") && <div className="flex gap-2 mt-1"><input aria-label={`Invite email for ${workspace.name}`} type="email" placeholder="teammate@example.com" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" /><button type="button" disabled={!inviteEmail.trim()} onClick={() => createInvite(workspace)} className="px-2 py-1 rounded bg-slate-700 text-white text-xs disabled:opacity-50">Create invite</button></div>}{(members[workspace.id] ?? []).map((member) => <div key={member.user_id} className="mt-2 flex items-center gap-2 text-[11px] text-slate-500"><span className="flex-1">{member.email}</span><select aria-label={`Role for ${member.email}`} value={member.role} disabled={member.role === "owner"} onChange={(event) => updateMember(workspace, member, event.target.value)} className="px-1 py-0.5 border border-slate-300 rounded text-[11px]"><option value="member">member</option><option value="admin">admin</option><option value="owner">owner</option></select>{member.role !== "owner" && <button type="button" onClick={() => removeMember(workspace, member)} className="text-red-600 underline">Remove</button>}</div>)}{(invitations[workspace.id] ?? []).map((invitation) => <div key={invitation.id} className="mt-2 flex items-center justify-between text-[11px] text-slate-500"><span>Pending: {invitation.email} · {invitation.role}</span><button type="button" onClick={() => revokeInvite(workspace, invitation)} className="text-red-600 underline">Revoke</button></div>)}</div>)}</div>}
        {workspaces.length > 0 && <div className="mt-3 flex gap-2"><input aria-label="New workspace name" value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} placeholder="New workspace name" className="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" /><button type="button" disabled={workspaceName.trim().length < 2} onClick={createWorkspace} className="px-2 py-1 rounded bg-sky-600 text-white text-xs disabled:opacity-50">Create workspace</button></div>}
        {generatedToken && <div role="status" className="mt-3 border border-amber-200 bg-amber-50 rounded-lg p-3"><div className="flex items-center justify-between gap-3"><p className="text-xs font-semibold text-amber-900">Share this invitation token</p><button type="button" onClick={copyInvitationToken} className="shrink-0 rounded border border-amber-300 bg-white px-2 py-1 text-[11px] font-medium text-amber-900 hover:bg-amber-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500">Copy token</button></div><p className="mt-1 text-[11px] text-amber-800">It expires in 7 days and can only be accepted by the invited email address.</p><code className="block mt-2 break-all rounded bg-white/70 p-2 text-[11px] text-amber-800">{generatedToken}</code></div>}
        {workspaces.length > 0 && <div className="mt-4 border border-sky-200 bg-sky-50 rounded-lg p-3"><p className="text-xs font-semibold text-sky-900">Accept an invitation</p><div className="flex gap-2 mt-1"><input aria-label="Workspace invitation token" value={inviteToken} onChange={(e) => setInviteToken(e.target.value)} placeholder="Paste invitation token" className="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" /><button type="button" disabled={!inviteToken.trim()} onClick={acceptInvite} className="px-2 py-1 rounded bg-sky-600 text-white text-xs disabled:opacity-50">Accept</button></div></div>}
        {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
        <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setMessage(null); setError(null); }} className="mt-5 text-sm text-sky-700 underline">{mode === "login" ? "Create a new account" : "Use an existing account"}</button>
      </div>
    </div>
  );
}
