'use client'
import { useState, useEffect, useRef } from 'react';
import { trackBalls, controlServo, updateBallParams } from './services/api';

interface Ball {
  x: number;
  y: number;
  color: string;
  radius: number;
}

interface BallDetectionParams {
  min_radius: number;
  max_radius: number;
}

export default function Home() {
  const [balls, setBalls] = useState<Ball[]>([]);
  const [totalBalls, setTotalBalls] = useState(0);
  const [frame, setFrame] = useState('');
  const [servoAngle, setServoAngle] = useState(90);
  const [ballParams, setBallParams] = useState<BallDetectionParams>({
    min_radius: 15,
    max_radius: 30
  });
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await trackBalls();
        setBalls(data.balls);
        setTotalBalls(data.total_balls);
        setFrame(data.frame);
      } catch (error) {
        console.error('Failed to track balls:', error);
      }
    }, 100); // Increase update frequency to 10 times per second

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (frame && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        const img = new Image();
        img.onload = () => {
          canvas.width = img.width;
          canvas.height = img.height;
          ctx.drawImage(img, 0, 0);
          
          // Draw circles for detected balls
          balls.forEach(ball => {
            ctx.beginPath();
            ctx.arc(ball.x, ball.y, ball.radius, 0, 2 * Math.PI);
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.fillStyle = 'white';
            ctx.fillText(ball.color, ball.x - 20, ball.y - ball.radius - 5);
          });
        };
        img.src = `data:image/jpeg;base64,${frame}`;
      }
    }
  }, [frame, balls]);

  const handleServoControl = async () => {
    try {
      await controlServo(servoAngle);
    } catch (error) {
      console.error('Failed to control servo:', error);
    }
  };

  const handleBallParamsUpdate = async () => {
    try {
      await updateBallParams(ballParams);
    } catch (error) {
      console.error('Failed to update ball parameters:', error);
    }
  };

  return (
    <div className="min-h-screen p-8 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-8 items-center">
        <h1 className="text-3xl font-bold">Pingpong Ball Feeder System</h1>
        <div className="bg-gray-100 p-4 rounded-lg">
          <h2 className="text-xl font-semibold mb-2">Camera Feed</h2>
          <canvas ref={canvasRef} className="w-full max-w-lg" />
        </div>
        <div className="bg-gray-100 p-4 rounded-lg">
          <h2 className="text-xl font-semibold mb-2">Detected Balls</h2>
          <p>Total Balls: {totalBalls}</p>
          <ul>
            {balls.map((ball, index) => (
              <li key={index}>
                Ball at x: {ball.x}, y: {ball.y}, color: {ball.color}, radius: {ball.radius}
              </li>
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
        <div className="flex flex-col items-center gap-4">
          <h2 className="text-xl font-semibold">Ball Detection Parameters</h2>
          <div className="flex flex-col gap-2">
            <label>
              Min Radius:
              <input
                type="number"
                value={ballParams.min_radius}
                onChange={(e) => setBallParams({...ballParams, min_radius: parseInt(e.target.value)})}
                className="ml-2 p-1 border rounded"
              />
            </label>
            <label>
              Max Radius:
              <input
                type="number"
                value={ballParams.max_radius}
                onChange={(e) => setBallParams({...ballParams, max_radius: parseInt(e.target.value)})}
                className="ml-2 p-1 border rounded"
              />
            </label>
          </div>
          <button
            onClick={handleBallParamsUpdate}
            className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
          >
            Update Ball Parameters
          </button>
        </div>
      </main>
    </div>
  );
}
