import time
from datetime import datetime
import board
import adafruit_dht
import smbus2
import tkinter as tk
import threading
from tkinter import ttk
from gpiozero import MotionSensor
from RPLCD.i2c import CharLCD
import mysql.connector

class UnifiedStudyHelper:
    def __init__(self, root):
        # Add login state variables
        self.login_complete = False
        self.running = True
        self.active_mode = False
        self.break_active = False
        self.timer_running = True
        
        # Session tracking
        self.start_time = None
        self.session_start_time = None
        self.session_elapsed_time = 0
        self.last_sensor_read_time = 0
        self.total_active_time = 0
        self.progress_value = 0
        
        # Initialize data tracking
        self.session_data = {
            "temp_total": 0, 
            "hum_total": 0, 
            "lux_total": 0, 
            "readings_count": 0
        }

        # Initialize hardware and connections
        self._init_hardware()
        self._init_database()
        
        # Initialize GUI
        self.root = root
        self.root.title("Study Helper")
        self.root.geometry("700x550")
        self.setup_gui()
        
        # Start sensor thread
        self.sensor_thread = threading.Thread(target=self.sensor_loop, daemon=True)
        self.sensor_thread.start()

    def _init_hardware(self):
        """Initialize hardware components"""
        self.dhtDevice = adafruit_dht.DHT11(board.D4)
        self.pir = MotionSensor(17)
        self.I2C_ADDR = 0x4b
        self.bus = smbus2.SMBus(1)
        self.lcd = CharLCD(
            i2c_expander='PCF8574', 
            address=0x27, 
            port=1,
            cols=16, 
            rows=2, 
            charmap='A00', 
            auto_linebreaks=True
        )
        self.lcd.clear()
        self.pir.when_motion = self.motion_detected

    def _init_database(self):
        """Initialize database connection"""
        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Fg110085060",
            database="studyhelper"
        )

    def setup_gui(self):
        """Initialize all GUI components"""
        self.enable_dark_mode()
        
        # Configure Grid Columns
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(6, weight=1)

        # Login Screen
        self.login_frame = tk.Frame(self.root, bg='#2E2E2E')
        self.login_frame.pack(expand=True)
        
        self.name_label = tk.Label(self.login_frame, text="Enter Your Name:", fg='white', bg='#2E2E2E')
        self.name_label.pack(pady=5)
        
        self.name_entry = tk.Entry(self.login_frame, bg='#555', fg='white', insertbackground='white')
        self.name_entry.pack(pady=5)
        
        self.submit_button = tk.Button(self.login_frame, text="Submit", command=self.start_app, 
                                     bg='#444', fg='white', activebackground='#666')
        self.submit_button.pack(pady=5)

        # Initialize other GUI variables
        self.break_active = False
        self.progress_value = 0
        self.running = True
        self.timer_running = True
        self.session_elapsed_time = 0

    def start_app(self):
        """Initialize main application after login"""
        self.user_name = self.name_entry.get() or "Guest"
        self.session_start_time = time.time()
        self.login_frame.destroy()

            # Timer Variables
        self.session_start_time = time.time()  # Store when the app starts
        self.session_elapsed_time = 0  # Track elapsed time
        self.timer_running = True  # Controls whether the timer is running
        self.login_frame.destroy()
        
        # Title Label
        self.title_label = tk.Label(self.root, text="Study Helper", font=("Arial", 16, "bold"), fg='white', bg='#2E2E2E')
        self.title_label.grid(row=0, column=0, columnspan=2, pady=10, sticky="n")

        # Top Frame (For Progress Bar & Clock)
        self.top_frame = tk.Frame(self.root, bg='#2E2E2E')
        self.top_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=10)
        self.top_frame.columnconfigure(1, weight=1)  # Allow stretching for right alignment

        # Progress Bar Frame (Styled Box)
        self.progress_frame = tk.LabelFrame(self.top_frame, text="Time Until Next Break", 
                                            font=("Arial", 8, "bold"), fg="white", bg='#2E2E2E',
                                            labelanchor="n", bd=2, relief=tk.GROOVE)
        self.progress_frame.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Progress Bar Inside Frame
        self.progress = ttk.Progressbar(self.progress_frame, length=200, mode='determinate')
        self.progress.pack(padx=10, pady=5)

        # Clock Frame (Styled Box)
        self.clock_frame = tk.LabelFrame(self.top_frame, text="Current Time", 
                                         font=("Arial", 8, "bold"), fg="white", bg='#2E2E2E', 
                                         labelanchor="n", bd=2, relief=tk.GROOVE)
        self.clock_frame.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # Clock Label Inside Frame
        self.clock_label = tk.Label(self.clock_frame, text="", font=("Arial", 12, "bold"), 
                                    fg='#00FF00', bg='#222', padx=10, pady=5)
        self.clock_label.pack(padx=5, pady=5)

        # Data Frame (Now with 3 values)
        self.data_frame = tk.LabelFrame(self.root, text="Environmental Data", 
                                        font=("Arial", 10, "bold"), fg="white", bg='#444', 
                                        labelanchor="n", bd=2, relief=tk.GROOVE)
        self.data_frame.grid(row=3, column=0, columnspan=2, pady=50, padx=10, sticky='nsew')

        # Allow both columns to expand so labels stay aligned
        self.data_frame.columnconfigure(0, weight=1)  # Left side expands
        self.data_frame.columnconfigure(1, weight=3)  # Right side expands

        # ======= Temperature Row =======
        self.temp_frame = tk.Frame(self.data_frame, bg='#444')
        self.temp_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.temp_frame.columnconfigure(1, weight=1)

        self.temp_label = tk.Label(self.temp_frame, text="Temperature: --°C", font=("Arial", 12, "bold"), 
                                fg='#FFA500', bg='#444')
        self.temp_label.grid(row=0, column=0, sticky="w")

        self.temp_avg_label = tk.Label(self.temp_frame, text="Avg. Temp: --°C", font=("Arial", 12, "bold"), 
                                    fg='#FFA500', bg='#444')
        self.temp_avg_label.grid(row=0, column=1, sticky="e")

        # ======= Humidity Row =======
        self.humidity_frame = tk.Frame(self.data_frame, bg='#444')
        self.humidity_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.humidity_frame.columnconfigure(1, weight=1)

        self.humidity_label = tk.Label(self.humidity_frame, text="Humidity: --%", font=("Arial", 12, "bold"), 
                                    fg='#00FFFF', bg='#444')
        self.humidity_label.grid(row=0, column=0, sticky="w")

        self.humidity_avg_label = tk.Label(self.humidity_frame, text="Avg. Hum: --%", font=("Arial", 12, "bold"), 
                                        fg='#00FFFF', bg='#444')
        self.humidity_avg_label.grid(row=0, column=1, sticky="e")

        # ======= Lux Row =======
        self.lux_frame = tk.Frame(self.data_frame, bg='#444')
        self.lux_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.lux_frame.columnconfigure(1, weight=1)

        self.lux_label = tk.Label(self.lux_frame, text="Lux: -- lx", font=("Arial", 12, "bold"), 
                                fg='#FFD700', bg='#444')
        self.lux_label.grid(row=0, column=0, sticky="w")

        self.lux_avg_label = tk.Label(self.lux_frame, text="Avg. Lux: -- lx", font=("Arial", 12, "bold"), 
                                    fg='#FFD700', bg='#444')
        self.lux_avg_label.grid(row=0, column=1, sticky="e")

        # Session Timer Frame
        self.timer_frame = tk.LabelFrame(self.root, text="Session Time", font=("Arial", 10, "bold"), 
                                         fg="white", bg='#2E2E2E', bd=2, relief=tk.GROOVE, labelanchor="n")
        self.timer_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))

        #Session Timer Inside Frame
        self.timer_label = tk.Label(self.timer_frame, text="Elapsed Time: 00:00", font=("Arial", 12, "bold"), 
                                    fg='#00FF00', bg='#222', padx=10, pady=5)
        self.timer_label.pack(padx=5, pady=5)
        
        # Break Button (Centered)
        self.break_button = tk.Button(self.root, text="Take a Break", command=self.start_break, bg='#444', fg='white', activebackground='#666')
        self.break_button.grid(row=5, column=0, columnspan=2, pady=10, sticky="n")

        # Break Mode Indicator (Centered)
        self.break_label = tk.Label(self.root, text="", font=("Arial", 12, "bold"), fg="red", bg='#2E2E2E')
        self.break_label.grid(row=6, column=0, columnspan=2)

        # User Name Display (Bottom Left)
        self.user_label = tk.Label(self.root, text=f"User: {self.user_name}", font=("Arial", 10), fg='white', bg='#2E2E2E')
        self.user_label.grid(row=7, column=0, pady=10, sticky="sw")

        # Quit Button (Bottom Right)
        self.quit_button = tk.Button(self.root, text="Quit", command=self.on_close, bg='#444', fg='white', activebackground='#666')
        self.quit_button.grid(row=7, column=1, pady=10, sticky="se")

        # Initialize variables
        self.break_active = False
        self.progress_value = 0
        self.running = True
    
        # Only start clock update, other updates will start when motion is detected
        self.update_clock()
        self.update_data()  # Initial call to setup display with "--" values

        # Set login complete flag after GUI is fully setup
        self.login_complete = True
        
        # Start updates
        self.update_clock()
        self.update_data()

    # Enable Dark Mode
    def enable_dark_mode(self):
        self.root.configure(bg='#2E2E2E')

    # Read from ADS7830 channel
    def read_adc(self, channel):
        """Read from ADS7830 channel"""
        if channel < 0 or channel > 7:
            raise ValueError("Channel must be between 0 and 7.")
        command = 0x84 | (channel << 4)
        return self.bus.read_byte_data(self.I2C_ADDR, command)

    # Display message on LCD
    def display_lcd(self, message, duration=2):
        """Display message on LCD"""
        self.lcd.clear()
        lines = message.split('\n')
        self.lcd.write_string(lines[0])
        if len(lines) > 1:
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(lines[1])
        print(f"LCD Display: {message}")
        time.sleep(duration)

    # Fetch the most recent sensor data from the database
    def motion_detected(self):
        """Handle motion detection"""
        # Ignore motion events before login is complete
        if not self.login_complete:
            return
            
        print("Motion Detected!")
        if not self.active_mode:
            self.active_mode = True
            # Ensure database connection when waking up
            self.ensure_connection()
            
            self.start_time = datetime.now()
            self.session_start_time = time.time()
            self.session_start_time = time.time()  # Reset session start time
            self.session_elapsed_time = 0  # Reset elapsed time
            self.total_active_time = 0
            self.progress_value = 0  # Reset progress bar
            self.session_data = {"temp_total": 0, "hum_total": 0, "lux_total": 0, "readings_count": 0}
            
            # Start timers and progress bar
            self.timer_running = True
            self.update_timer()
            self.update_progress()
            
            self.display_lcd("Welcome!\nSensors Active", duration=3)
            print("System activated.")
        else:
            self.start_time = datetime.now()  # Reset idle timer
            print("Motion detected. Idle timer reset.")

    def sensor_loop(self):
        """Main sensor reading and data collection loop"""
        while self.running:
            try:
                if self.active_mode and not self.break_active:
                    current_time = time.time()
                    
                    if current_time - self.last_sensor_read_time >= 2:
                        try:
                            # Read sensors
                            temperature_c = self.dhtDevice.temperature
                            humidity = self.dhtDevice.humidity
                            
                            # Read light sensor
                            raw_value = self.read_adc(0)
                            voltage = raw_value * 3.3 / 255
                            lux = voltage * (1000 / 3.3)
                            
                            # Display on LCD
                            self.display_lcd(f"Temp: {temperature_c}C\nHum: {humidity}%", duration=2)
                            self.display_lcd(f"Light Level:\n{lux:.1f} lx", duration=2)
                            
                            # Ensure database connection and store readings
                            self.ensure_connection()
                            cursor = self.conn.cursor()
                            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Insert new reading
                            sql = """INSERT INTO readings (time, temperature_c, humidity, lux) 
                                    VALUES (%s, %s, %s, %s)"""
                            val = (current_timestamp, temperature_c, humidity, lux)
                            cursor.execute(sql, val)
                            self.conn.commit()
                            cursor.close()
                            
                            print(f"Sensor Data - Temp: {temperature_c:.1f}C, Humidity: {humidity}%, Lux: {lux:.1f}")
                            print("Data successfully logged to database")
                            
                            self.last_sensor_read_time = current_time
                            
                        except RuntimeError as error:
                            print(f"Sensor error: {error.args[0]}")
                            time.sleep(2.0)
                        except mysql.connector.Error as error:
                            print(f"Database error: {error}")
                        except Exception as error:
                            print(f"Other error: {error}")
                    
                    # Check for idle timeout
                    if (datetime.now() - self.start_time).seconds > 90:
                        print("No motion detected for 30 seconds - entering idle mode")
                        self.active_mode = False
                        self.timer_running = False
                        self.progress_value = 0
                        self.progress["value"] = 0
                        self.session_elapsed_time = 0
                        self.display_session_summary()
                        
                else:
                    self.idle_animation()
                    
                time.sleep(1)
                
            except Exception as e:
                print(f"Error in sensor loop: {e}")
                time.sleep(1)

    def update_data(self):
        """Update GUI with data from database"""
        if self.running and self.active_mode:
            try:
                self.ensure_connection()
                cursor = self.conn.cursor()
                
                # Get latest reading
                cursor.execute("""
                    SELECT temperature_c, humidity, lux
                    FROM readings 
                    WHERE time >= %s
                    ORDER BY time DESC 
                    LIMIT 1
                """, (datetime.fromtimestamp(self.session_start_time),))
                current = cursor.fetchone()
                
                # Get averages separately
                cursor.execute("""
                    SELECT AVG(temperature_c), AVG(humidity), AVG(lux)
                    FROM readings
                    WHERE time >= %s
                """, (datetime.fromtimestamp(self.session_start_time),))
                averages = cursor.fetchone()
                
                if current and averages and all(x is not None for x in current + averages):
                    current_temp, current_hum, current_lux = current
                    avg_temp, avg_hum, avg_lux = averages
                    
                    # Update current values if not on break
                    if not self.break_active:
                        try:
                            self.temp_label.config(text=f"Temperature: {current_temp:.1f}°C")
                            self.humidity_label.config(text=f"Humidity: {current_hum:.1f}%")
                            self.lux_label.config(text=f"Lux: {current_lux:.1f} lx")
                        except (TypeError, ValueError) as e:
                            print(f"Error updating current values: {e}")
                    
                    # Update averages
                    try:
                        self.temp_avg_label.config(text=f"Avg. Temp: {avg_temp:.1f}°C")
                        self.humidity_avg_label.config(text=f"Avg. Hum: {avg_hum:.1f}%")
                        self.lux_avg_label.config(text=f"Avg. Lux: {avg_lux:.1f} lx")
                    except (TypeError, ValueError) as e:
                        print(f"Error updating averages: {e}")
                
                cursor.close()
                
            except mysql.connector.Error as e:
                print(f"Database error: {e}")
            except Exception as e:
                print(f"Unexpected error in update_data: {e}")

            self.root.after(1000, self.update_data)
        else:
            # Reset labels when not active
            self.temp_label.config(text="Temperature: --°C")
            self.humidity_label.config(text="Humidity: --%")
            self.lux_label.config(text="Lux: -- lx")
            self.temp_avg_label.config(text="Avg. Temp: --°C")
            self.humidity_avg_label.config(text="Avg. Hum: --%")
            self.lux_avg_label.config(text="Avg. Lux: -- lx")
            self.root.after(1000, self.update_data)

    # Update the clock label
    def update_clock(self):
        """Updates the clock label with the current time every second."""
        current_time = datetime.now().strftime('%I:%M:%S %p')
        self.clock_label.config(text=current_time)
        self.root.after(1000, self.update_clock)

    # Update the session timer
    def update_timer(self):
        """Updates the session timer every second"""
        if self.timer_running and self.active_mode and not self.break_active:
            elapsed = int(time.time() - self.session_start_time + self.session_elapsed_time)
            minutes, seconds = divmod(elapsed, 60)
            self.timer_label.config(text=f"Elapsed Time: {minutes:02d}:{seconds:02d}")
            self.total_active_time = elapsed
            self.root.after(1000, self.update_timer)
        elif self.active_mode:  # Keep checking if system is active
            self.root.after(1000, self.update_timer)
        else:
            self.timer_label.config(text="Elapsed Time: 00:00")  # Reset display when inactive

    # Update the progress bar
    def update_progress(self):
        """Updates the progress bar gradually and triggers a break when full"""
        if not self.break_active and self.running and self.active_mode:
            self.progress_value += 1
            if self.progress_value > 100:
                self.start_break()
                return
            self.progress["value"] = self.progress_value
            self.root.after(500, self.update_progress)
        elif self.active_mode:  # Keep checking if system is active
            self.root.after(500, self.update_progress)
        else:
            self.progress_value = 0
            self.progress["value"] = 0
    
    # Start a 5 second break
    def start_break(self):
        """Triggers a 5-minute break where sensor readings are paused."""
        if not self.break_active:
            self.break_active = True
            self.break_label.config(text="Break in Progress")
            self.timer_running = False  # Pause timer
            self.session_elapsed_time += time.time() - self.session_start_time  # Save elapsed time
            self.progress["value"] = 0
            
            # Display break message on LCD
            self.display_lcd("Break Time!\nRelax...", duration=2)
            # Start break timer immediately
            threading.Thread(target=self.break_timer, daemon=True).start()

    # Break timer
    def break_timer(self):
        """Handles the break duration and resumes updates after 5 minutes."""
        start_time = time.time()
        while time.time() - start_time < 5 and self.break_active:  # 5 minutes = 300 seconds
            remaining = int(5 - (time.time() - start_time))
            mins, secs = divmod(remaining, 60)
            self.break_label.config(text=f"Break Time: {mins:02d}:{secs:02d}")
            time.sleep(1)
        
        if self.break_active:  # Only resume if break wasn't interrupted
            # Resume normal operation
            self.session_start_time = time.time()  # Restart timer
            self.timer_running = True  # Resume timer
            self.progress_value = 0
            self.break_active = False
            self.break_label.config(text="")
            
            # Restart the progress
            self.update_progress()
            self.display_lcd("Break Over!\nResuming...", duration=2)

    # Function to retrieve environmental suggestions
    def get_suggestions(self, temp, hum, lux):
        suggestions = []
        if temp > 30:
            suggestions.append("Turn on the fan")
        elif temp < 18:
            suggestions.append("Turn on the heater")
        if hum < 1:
            suggestions.append("Turn on a humidifier")
        elif hum > 70:
            suggestions.append("Turn off a humidifier")
        if lux < 100:
            suggestions.append("Turn on a lamp")
        elif lux > 1000:
            suggestions.append("Reduce lighting")
        return suggestions

    # Rotate default messages during active mode
    def rotate_default_message(self, data):
        minutes, seconds = divmod(self.total_active_time, 60)
        messages = [
            f"Time Active: {minutes:02}:{seconds:02}",
           f"Temp: {data['temperature_c']:.1f}",
            f"Humidity: {data['humidity']}",
            f"Lux: {data['lux']:.1f}"
        ]
        self.display_lcd(messages[self.default_cycle_index], duration=2)
        self.default_cycle_index = (self.default_cycle_index + 1) % len(messages)

    # Idle state animation
    def idle_animation(self):
        while not self.active_mode and self.running:
            for dots in range(1, 4):
                self.display_lcd(f"Sleeping{'.' * dots}")
                time.sleep(1)
                if self.active_mode:  # Break animation if system activates
                    break

    # Session summary
    def display_session_summary(self):
        """Display session summary with accurate timing from GUI timer"""
        elapsed = int(time.time() - self.session_start_time + self.session_elapsed_time)
        minutes, seconds = divmod(elapsed, 60)
        
        self.display_lcd("Study Session\nSummary", duration=3)
        self.display_lcd(f"Total Time:\n{minutes:02d}m {seconds:02d}s", duration=3)

        if self.session_data["readings_count"] > 0:
            avg_temp = self.session_data["temp_total"] / self.session_data["readings_count"]
            avg_hum = self.session_data["hum_total"] / self.session_data["readings_count"]
            avg_lux = self.session_data["lux_total"] / self.session_data["readings_count"]
            
            # Display environmental data and suggestions
            self.display_lcd(f"Temp Avg:\n{avg_temp:.1f}C", duration=3)
            self.display_lcd(f"Humidity Avg:\n{avg_hum:.1f}%", duration=3)
            self.display_lcd(f"Light Avg:\n{avg_lux:.1f}lx", duration=3)
            
            # Add environmental suggestions based on averages
            suggestions = []
            if avg_temp > 25:
                suggestions.append("Room too warm\nOpen window")
            elif avg_temp < 20:
                suggestions.append("Room too cold\nHeat needed")
            if avg_hum > 60:
                suggestions.append("Too humid\nVentilate room")
            elif avg_hum < 40:
                suggestions.append("Air too dry\nUse humidifier")
            if avg_lux < 300:
                suggestions.append("Light too low\nIncrease lighting")
            elif avg_lux > 1000:
                suggestions.append("Light too bright\nReduce glare")
                
            # Display suggestions
            for suggestion in suggestions:
                self.display_lcd(suggestion, duration=3)
                
        self.display_lcd("Session ended\nGoodbye!", duration=3)

    # Ensure MySQL connection is active, reconnect if needed
    def export(self):
        """Ensure MySQL connection is active, reconnect if needed"""
        try:
            if not self.conn.is_connected():
                print("Reconnecting to MySQL...")
                self.conn.ping(reconnect=True)
                if self.conn.is_connected():
                    print("Reconnected successfully!")
        except mysql.connector.Error as err:
            print(f"MySQL Error: {err}")
            try:
                self.conn = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="Fg110085060",
                    database="studyhelper"
                )
                print("New connection established!")
            except mysql.connector.Error as err:
                print(f"Failed to reconnect: {err}")

    # Clean up resources and close program
    def on_close(self):
        """Clean up resources and close program"""
        self.running = False
        try:
            self.dhtDevice.exit()
            self.bus.close()
            self.conn.close()
            self.lcd.clear()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        print("Resources released. Program terminated.")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = UnifiedStudyHelper(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()