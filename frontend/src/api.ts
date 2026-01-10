import type { QueryResponse } from './types';

// Use /api prefix in production (Docker), direct URL in development
const API_BASE_URL = import.meta.env.PROD ? '/api' : 'http://localhost:8000';

export async function askQuestion(question: string): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
