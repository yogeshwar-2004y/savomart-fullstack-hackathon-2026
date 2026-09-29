export type DemoIdentity = { role: string; userId: string };

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function setDemoIdentity(identity: DemoIdentity) {
  window.localStorage.setItem("sitescout-role", identity.role);
  window.localStorage.setItem("sitescout-user-id", identity.userId);
}

function authHeaders(): Record<string, string> {
  return {
    "X-Demo-Role": window.localStorage.getItem("sitescout-role") ?? "bd-manager",
    "X-Demo-User-Id": window.localStorage.getItem("sitescout-user-id") ?? "bd-manager-1"
  };
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders(), ...(options?.headers as Record<string, string> | undefined) };
  if (!(options?.body instanceof FormData)) headers["Content-Type"] = "application/json";
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/api/v1${path}`, { ...options, headers });
  } catch (reason) {
    if (reason instanceof TypeError) throw new Error("Backend unavailable. Check the local API service and retry.");
    throw reason;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    if (Array.isArray(detail)) throw new Error(detail.map((item) => item.msg).join("; "));
    throw new Error(detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export async function apiPhoto(path: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl}${path}`, { headers: authHeaders() });
  if (!response.ok) throw new Error("Photo unavailable");
  return URL.createObjectURL(await response.blob());
}
