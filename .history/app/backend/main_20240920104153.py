from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import RPi.GPIO as GPIO
from pydantic import BaseModel

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

# Set up GPIO for servo control
GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.OUT)
servo = GPIO.PWM(25, 50)  # 50 Hz frequency
servo.start(0)

class ServoAngle(BaseModel):
    angle: int

@app.get("/")
async def read_root():
    return {"message": "Pingpong Ball Feeder System API"}

@app.get("/track-balls")
async def track_balls():
    # Capture frame-by-frame
    ret, frame = camera.read()
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to capture image")
    
    # Convert BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Define range of orange color in HSV
    lower_orange = np.array([5, 50, 50])
    upper_orange = np.array([15, 255, 255])
    
    # Threshold the HSV image to get only orange colors
    mask = cv2.inRange(hsv, lower_orange, upper_orange)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    balls = []
    for contour in contours:
        # Calculate centroid
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            balls.append({"x": cx, "y": cy})
    
    return {"balls": balls}

@app.post("/control-servo")
async def control_servo(servo_angle: ServoAngle):
    if servo_angle.angle < 0 or servo_angle.angle > 180:
        raise HTTPException(status_code=400, detail="Angle must be between 0 and 180")
    
    duty = servo_angle.angle / 18 + 2
    servo.ChangeDutyCycle(duty)
    return {"message": f"Servo moved to {servo_angle.angle} degrees"}

@app.on_event("shutdown")
def shutdown_event():
    servo.stop()
    GPIO.cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)