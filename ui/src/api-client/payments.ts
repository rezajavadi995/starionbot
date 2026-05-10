export async function createStarsInvoice(userId: number, amountXtr: number) {
  const response = await fetch('/crash/stars/invoice', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, amount_xtr: amountXtr }),
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || 'failed to create stars invoice');
  }
  return response.json() as Promise<{
    title: string;
    description: string;
    payload: string;
    currency: 'XTR';
    prices: Array<{ label: string; amount: number }>;
  }>;
}
