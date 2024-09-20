from fastapi import FastAPI, HTTPException, Query
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check if running on Raspberry Pi
is_raspberry_pi = platform.machine().startswith('arm')

if is_raspberry_pi:
    import RPi.GPIO as GPIO
    from opcua import Server
    
    # Set up GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(25, GPIO.OUT)
    pwm = GPIO.PWM(25, 50)
    pwm.start(0)
    
    # Set up OPC UA server
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    namespace = server.register_namespace("ServoControl")
    
    # Create objects and variables in OPC UA server
    objects = server.get_objects_node()
    servo_obj = objects.add_object(namespace, "ServoControl")
    start_servo_var = servo_obj.add_variable(namespace, "StartServo", False)
    speed_percentage_var = servo_obj.add_variable(namespace, "SpeedPercentage", 50)
    min_angle_var = servo_obj.add_variable(namespace, "MinSweepAngle", -45)
    max_angle_var = servo_obj.add_variable(namespace, "MaxSweepAngle", 45)
    
    # Set variables to be writable from the client
    start_servo_var.set_writable()
    speed_percentage_var.set_writable()
    min_angle_var.set_writable()
    max_angle_var.set_writable()
    
    # Shared variables for servo control
    shared_variables = {
        'speed_percentage': 50,
        'min_angle': -45,
        'max_angle': 45,
        'stop': True
    }
    
    def angle_to_duty_cycle(angle):
        return 2.5 + (angle + 60) * (10 / 120)
    
    def continuous_sweep(variables):
        try:
            while not variables['stop']:
                min_duty = angle_to_duty_cycle(variables['min_angle'])
                max_duty = angle_to_duty_cycle(variables['max_angle'])
                delay = (100 - variables['speed_percentage']) / 1000.0
    
                for duty_cycle in range(int(min_duty * 10), int(max_duty * 10) + 1):
                    if variables['stop']:
                        break
                    current_duty = duty_cycle / 10.0
                    pwm.ChangeDutyCycle(current_duty)
                    time.sleep(delay)
    
                for duty_cycle in range(int(max_duty * 10), int(min_duty * 10) - 1, -1):
                    if variables['stop']:
                        break
                    current_duty = duty_cycle / 10.0
                    pwm.ChangeDutyCycle(current_duty)
                    time.sleep(delay)
        
        except Exception as e:
            print(f"Error in sweeping: {e}")
        finally:
            pwm.ChangeDutyCycle(0)
    
    def opcua_monitor():
        global shared_variables
        running = False
        while True:
            try:
                start_servo = start_servo_var.get_value()
                speed_percentage = speed_percentage_var.get_value()
                min_angle = min_angle_var.get_value()
                max_angle = max_angle_var.get_value()
    
                shared_variables['speed_percentage'] = speed_percentage
                shared_variables['min_angle'] = min_angle
                shared_variables['max_angle'] = max_angle
    
                if start_servo and not running:
                    shared_variables['stop'] = False
                    print(f"Starting servo with speed: {speed_percentage}%, min_angle: {min_angle}, max_angle: {max_angle}")
                    sweep_thread = threading.Thread(target=continuous_sweep, args=(shared_variables,))
                    sweep_thread.start()
                    running = True
                elif not start_servo and running:
                    shared_variables['stop'] = True
                    print("Stopping servo.")
                    running = False
    
            except Exception as e:
                print(f"Error in OPC UA monitor: {e}")
    
            time.sleep(0.1)
    
    # Start OPC UA server
    server.start()
    print("OPC UA Server started at opc.tcp://0.0.0.0:4840/freeopcua/server/")
    
    # Start monitoring OPC UA variables in a separate thread
    monitor_thread = threading.Thread(target=opcua_monitor)
    monitor_thread.start()

else:
    print("Not running on Raspberry Pi. GPIO and OPC UA functionality will be simulated.")

# Initialize camera
camera = cv2.VideoCapture(0)

# Global variables for frame sharing
frame = None
frame_lock = threading.Lock()

# Define the color ranges (in HSV space)
color_ranges = {
    'red': [(0, 120, 70), (10, 255, 255)],
    'orange': [(10, 100, 20), (25, 255, 255)],
    'yellow': [(25, 100, 20), (35, 255, 255)],
    'green': [(35, 100, 20), (85, 255, 255)],
    'blue': [(85, 100, 20), (125, 255, 255)],
    'purple': [(125, 100, 20), (155, 255, 255)],
    'white': [(0, 0, 200), (180, 55, 255)]
}

class ServoAngle(BaseModel):
    angle: int

class Ball(BaseModel):
    x: int
    y: int
    color: str
    radius: int

class BallDetectionParams(BaseModel):
    min_radius: int = 15
    max_radius: int = 30
    dp: float = 1.2
    minDist: int = 50
    param1: int = 100
    param2: int = 30

ball_params = BallDetectionParams()

def detect_ball_color(hsv, mask):
    for color, (lower, upper) in color_ranges.items():
        lower_bound = np.array(lower, np.uint8)
        upper_bound = np.array(upper, np.uint8)
        color_mask = cv2.inRange(hsv, lower_bound, upper_bound)
        combined_mask = cv2.bitwise_and(mask, color_mask)
        if cv2.countNonZero(combined_mask) > 0:
            return color
    return "unknown"

def capture_frames():
    global frame
    while True:
        success, captured_frame = camera.read()
        if success:
            with frame_lock:
                frame = captured_frame
        time.sleep(0.03)

threading.Thread(target=capture_frames, daemon=True).start()

@app.get("/")
async def read_root():
    return {"message": "Pingpong Ball Feeder System API"}

def generate_frames():
    global frame
    while True:
        with frame_lock:
            if frame is not None:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if _:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.016)

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
    blurred_frame = cv2.GaussianBlur(current_frame, (15, 15), 0)
    gray_frame = cv2.cvtColor(blurred_frame, cv2.COLOR_BGR2GRAY)

    circles = cv2.HoughCircles(
        gray_frame,
        cv2.HOUGH_GRADIENT,
        dp=ball_params.dp,
        minDist=ball_params.minDist,
        param1=ball_params.param1,
        param2=ball_params.param2,
        minRadius=ball_params.min_radius,
        maxRadius=ball_params.max_radius
    )

    balls = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")

        for (x, y, r) in circles:
            mask = np.zeros(gray_frame.shape, dtype=np.uint8)
            cv2.circle(mask, (x, y), r, 255, -1)
            color = detect_ball_color(hsv, mask)
            cv2.circle(current_frame, (x, y), r, (0, 255, 0), 4)
            cv2.putText(current_frame, color, (x - r, y - r - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            balls.append(Ball(x=int(x), y=int(y), color=color, radius=int(r)))

    _, buffer = cv2.imencode('.jpg', current_frame)
    frame_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return {
        "balls": balls,
        "total_balls": len(balls),
        "frame": frame_base64
    }

@app.post("/update-ball-params")
async def update_ball_params(params: BallDetectionParams):
    global ball_params
    ball_params = params
    return {"message": "Ball detection parameters updated successfully"}

@app.post("/control-servo")
async def control_servo(servo_angle: ServoAngle):
    if servo_angle.angle < -60 or servo_angle.angle > 60:
        raise HTTPException(status_code=400, detail="Angle must be between -60 and 60")
    
    if is_raspberry_pi:
        duty_cycle = angle_to_duty_cycle(servo_angle.angle)
        pwm.ChangeDutyCycle(duty_cycle)
    else:
        print(f"Servo simulation: moved to {servo_angle.angle} degrees")
    
    return {"message": f"Servo moved to {servo_angle.angle} degrees"}

@app.on_event("shutdown")
def shutdown_event():
    if is_raspberry_pi:
        shared_variables['stop'] = True
        monitor_thread.join()
        server.stop()
        GPIO.cleanup()
        pwm.stop()
    camera.release()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)