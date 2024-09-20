from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import cv2
import numpy as np
from pydantic import BaseModel
import io
import base64
import platform
import threading
import time

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize camera
camera = cv2.VideoCapture(0)

# Global variables for frame sharing
frame = None
frame_lock = threading.Lock()

def capture_frames():
    global frame
    while True:
        success, captured_frame = camera.read()
        if success:
            with frame_lock:
                frame = captured_frame
        time.sleep(0.03)  # Capture at ~30 fps

# Start frame capture thread
threading.Thread(target=capture_frames, daemon=True).start()

class ServoAngle(BaseModel):
    angle: int

class Ball(BaseModel):
    x: int
    y: int
    color: str

@app.get("/")
async def read_root():
    return {"message": "Pingpong Ball Feeder System API"}

def generate_frames():
    global frame
    while True:
        with frame_lock:
            if frame is not None:
                success, buffer = cv2.imencode('.jpg', frame)
                if success:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.03)  # Stream at ~30 fps

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/track-balls")
async def track_balls():
    global frame
    with frame_lock:
        if frame is None:
            raise HTTPException(status_code=500, detail="No frame available")
        current_frame = frame.copy()
    
    hsv = cv2.cvtColor(current_frame, cv2.COLOR_BGR2HSV)
    
    # Define color ranges in HSV
    color_ranges = {
        "orange": ([5, 50, 50], [15, 255, 255]),
        "white": ([0, 0, 200], [180, 30, 255]),
        "yellow": ([20, 100, 100], [30, 255, 255])
    }
    
    balls = []
    for color, (lower, upper) in color_ranges.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # Minimum area to be considered a ball
                (x, y), radius = cv2.minEnclosingCircle(contour)
                center = (int(x), int(y))
                radius = int(radius)
                if 10 < radius < 50:  # Adjust these values based on your ping pong balls
                    cv2.circle(current_frame, center, radius, (0, 255, 0), 2)
                    cv2.putText(current_frame, color, (center[0] - 20, center[1] - radius - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    balls.append(Ball(x=int(x), y=int(y), color=color))
    
    # Encode frame as base64 for frontend display
    _, buffer = cv2.imencode('.jpg', current_frame)
    frame_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return {
        "balls": balls,
        "total_balls": len(balls),
        "frame": frame_base64
    }

@app.post("/control-servo")
async def control_servo(servo_angle: ServoAngle):
    if servo_angle.angle < 0 or servo_angle.angle > 180:
        raise HTTPException(status_code=400, detail="Angle must be between 0 and 180")
    
    if servo:
        duty = servo_angle.angle / 18 + 2
        servo.ChangeDutyCycle(duty)
        return {"message": f"Servo moved to {servo_angle.angle} degrees"}
    else:
        return {"message": f"Servo simulation: moved to {servo_angle.angle} degrees"}

@app.on_event("shutdown")
def shutdown_event():
    if servo:
        servo.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)