import { useCallback, useEffect, useState } from "react";

export type PairingWorkflowState =
  | { status: "loading" | "unpaired" | "paired" | "error"; message?: string }
  | { status: "code"; code: string; expiresAt: string; message?: string };

export function usePairingWorkflow(apiBaseUrl: string | undefined) {
  const [state, setState] = useState<PairingWorkflowState>({ status: "loading" });
  const refresh = useCallback(async (): Promise<void> => {
    if (!apiBaseUrl) {
      setState({ status: "error", message: "API 基础地址未配置。" });
      return;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/local/pairing/status`, { cache: "no-store" });
      const payload: unknown = await response.json();
      if (!response.ok || typeof payload !== "object" || payload === null) {
        throw new Error("无法读取本地配对状态。");
      }
      setState({ status: (payload as { paired?: boolean }).paired ? "paired" : "unpaired" });
    } catch (error: unknown) {
      setState({ status: "error", message: error instanceof Error ? error.message : "本地配对状态不可用。" });
    }
  }, [apiBaseUrl]);
  const createCode = useCallback(async (): Promise<void> => {
    if (!apiBaseUrl) return;
    try {
      const response = await fetch(`${apiBaseUrl}/local/pairing/session`, {
        method: "POST",
        headers: { "content-type": "application/json" },
      });
      const payload = (await response.json()) as { code?: string; expires_at?: string };
      if (!response.ok || !payload.code || !payload.expires_at) throw new Error("无法生成配对码。");
      setState({ status: "code", code: payload.code, expiresAt: payload.expires_at });
    } catch (error: unknown) {
      setState({ status: "error", message: error instanceof Error ? error.message : "配对失败。" });
    }
  }, [apiBaseUrl]);
  const revoke = useCallback(async (): Promise<void> => {
    if (!apiBaseUrl) return;
    await fetch(`${apiBaseUrl}/local/pairing/revoke`, { method: "POST" });
    await refresh();
  }, [apiBaseUrl, refresh]);
  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);
  return { state, createCode, revoke };
}
