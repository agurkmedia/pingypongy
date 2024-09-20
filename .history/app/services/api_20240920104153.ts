const API_URL = 'http://localhost:8000';

export async function trackBalls() {
  const response = await fetch(`${API_URL}/track-balls`);
  if (!response.ok) {
    throw new Error('Failed to track balls');
  }
  return response.json();
}

export async function controlServo(angle: number) {
  const response = await fetch(`${API_URL}/control-servo`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ angle }),
  });
  if (!response.ok) {
    throw new Error('Failed to control servo');
  }
  return response.json();
}