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

interface BallDetectionParams {
  min_radius: number;
  max_radius: number;
}

export const updateBallParams = async (params: BallDetectionParams) => {
  const response = await fetch(`${API_URL}/update-ball-params`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new Error('Failed to update ball parameters');
  }
  return await response.json();
};