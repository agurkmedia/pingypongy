'use client'
import { useState, useEffect } from 'react';
import { trackBalls, controlServo } from './services/api';

export default function Home() {
  const [balls, setBalls] = useState([]);
  const [servoAngle, setServoAngle] = useState(90);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await trackBalls();
        setBalls(data.balls);
      } catch (error) {
        console.error('Failed to track balls:', error);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleServoControl = async () => {
    try {
      await controlServo(servoAngle);
    } catch (error) {
      console.error('Failed to control servo:', error);
    }
  };

  return (
    <div className="min-h-screen p-8 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-8 items-center">
        <h1 className="text-3xl font-bold">Pingpong Ball Feeder System</h1>
        <div className="bg-gray-100 p-4 rounded-lg">
          <h2 className="text-xl font-semibold mb-2">Detected Balls</h2>
          <ul>
            {balls.map((ball, index) => (
              <li key={index}>Ball at x: {ball.x}, y: {ball.y}</li>
            ))}
          </ul>
        </div>
        <div className="flex flex-col items-center gap-4">
          <h2 className="text-xl font-semibold">Servo Control</h2>
          <input
            type="range"
            min="0"
            max="180"
            value={servoAngle}
            onChange={(e) => setServoAngle(parseInt(e.target.value))}
            className="w-64"
          />
          <button
            onClick={handleServoControl}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Set Servo Angle
          </button>
        </div>
      </main>
    </div>
  );
}
