const API_URL = 'http://localhost:8000';

export async function trackBalls() {
  const response = await fetch(`${API_URL}/track-balls`);
  if (!response.ok) {
    throw new Error('Failed to track balls');
  }
  return response.json();
}