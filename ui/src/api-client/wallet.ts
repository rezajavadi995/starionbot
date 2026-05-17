export async function getTonConnectConfig() {
  const response = await fetch('/crash/ton/connect-config');
  if (!response.ok) {
    throw new Error('failed to fetch ton connect config');
  }
  return response.json() as Promise<{ manifest_url: string; network: string }>;
}
