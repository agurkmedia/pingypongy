from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import cv2
import numpy as np
from pydantic import BaseModel
import io
import base64
import platform

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

# Conditional import and setup for Raspberry Pi
if platform.system() == "Linux" and platform.machine().startswith("arm"):
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(25, GPIO.OUT)
    servo = GPIO.PWM(25, 50)  # 50 Hz frequency
    servo.start(0)
else:
    print("Not running on Raspberry Pi. GPIO functionality will be simulated.")
    servo = None

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
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/track-balls")
async def track_balls():
    ret, frame = camera.read()
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to capture image")
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
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
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                balls.append(Ball(x=cx, y=cy, color=color))
    
    # Encode frame as base64 for frontend display
    _, buffer = cv2.imencode('.jpg', frame)
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