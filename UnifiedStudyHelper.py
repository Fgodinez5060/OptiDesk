"""
SWE-410: Smart Study Desk Assistant
Authors: Fernando Godinez
Due Date: 3/2/2025
This is my own work.
"""

import time
from datetime import datetime
import board
import adafruit_dht
import smbus2
from gpiozero import MotionSensor
from RPLCD.i2c import CharLCD
import mysql.connector

class StudyHelper:
    """Backend class handling all sensor interactions, data collection, and processing
    for the Study Helper application."""

    def __init__(self):
        """Initialize all sensors, database connection, and state variables:
        - Sets up DHT11 temperature/humidity sensor
        - Configures PIR motion sensor
        - Initializes I2C light sensor
        - Connects to MySQL database
        - Sets up LCD display
        - Initializes state tracking variables"""
        # Initialize sensor data for GUI
        self.current_reading = {"temperature_c": None, "humidity": None, "lux": None, "break_mode": False}
        self.current_avgs = {"temperature_c": None, "humidity": None, "lux": None}

        self.new_data = False

        # Timer Variables
        self.timer_running = False  # Start with timer off until motion detected
        self.session_start_time = None
        self.session_elapsed_time = 0  # This is a variable, not a function

        # Connect to the MySQL database
        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Fg110085060",
            database="studyhelper"
        )
        if self.conn.is_connected():
            print("Connected to MySQL!")
        
        # Initialize DHT11 sensor on GPIO4
        self.dhtDevice = adafruit_dht.DHT11(board.D4)
        
        # Initialize PIR sensor on GPIO17
        self.pir = MotionSensor(17)
        print("PIR Sensor initializing... Please wait.")
        self.pir.wait_for_no_motion()
        print("PIR Sensor ready. Monitoring for motion...")
        
        # I2C setup for light sensor (ADS7830)
        self.I2C_ADDR = 0x4b  # Default I2C address for ADS7830
        self.bus = smbus2.SMBus(1)
        
        # Initialize LCD (I2C interface)
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
        
        # Variables for state management
        self.active_mode = False  # Start inactive until motion detected
        self.start_time = None  # Initialize as None
        self.last_motion_time = None  # Add this to track last motion
        self.last_sensor_read_time = 0  # Tracks the last time data was read
        self.default_cycle_index = 0   # Index for rotating default messages
        self.total_active_time = 0     # Tracks the total active time in seconds
        
        # Statistics for session summary
        self.session_data = {"temp_total": 0, "hum_total": 0, "lux_total": 0, "readings_count": 0}
        
        # Set up the PIR motion callback
        self.pir.when_motion = self.motion_detected

        self.current_lcd_message = ""  # Add this to track current LCD message

        # Add break state
        self.break_mode = False
        self.break_duration = 5  # 5 seconds for testing
        self.break_start_time = None
        self.total_break_time = 0

    def read_adc(self, channel):
        """Read analog value from ADS7830 ADC.
        Args:
            channel: ADC channel number (0-7)
        Returns:
            int: Raw ADC value"""
        if channel < 0 or channel > 7:
            raise ValueError("Channel must be between 0 and 7.")
        command = 0x84 | (channel << 4)  # Command format for ADS7830
        return self.bus.read_byte_data(self.I2C_ADDR, command)

    def display_lcd(self, message, duration=2):
        """Display message on LCD screen and store for GUI.
        Args:
            message: String to display
            duration: How long to show message (seconds)"""
        self.lcd.clear()
        self.lcd.write_string(message)
        self.current_lcd_message = message  # Store current message
        print(f"LCD Display: {message}")
        time.sleep(duration)

    def get_lcd_message(self):
        """Return the current LCD message for GUI."""
        return self.current_lcd_message

    def fetch_latest_data(self):
        """Fetch the most recent sensor data from the database."""
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM readings ORDER BY time DESC LIMIT 1")
            result = cursor.fetchone()
            return result if result else {"temperature_c": None, "humidity": None, "lux": None}
        except mysql.connector.Error as e:
            print(f"Database error while fetching latest data: {e}")
            return {"temperature_c": None, "humidity": None, "lux": None}
        finally:
            if cursor:
                cursor.close()

    def get_suggestions(self, temp, hum, lux):
        """Generate environmental suggestions based on sensor readings.
        Args:
            temp: Temperature in Celsius
            hum: Relative humidity percentage
            lux: Light level in lux
        Returns:
            list: Suggested actions for optimal study conditions"""
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

    def motion_detected(self):
        """Handle motion detection events:
        - Activates system if inactive
        - Resets idle timer
        - Starts session timing"""
        current_time = datetime.now()
        self.last_motion_time = current_time  # Update last motion time
        
        if not self.active_mode:
            self.active_mode = True
            self.timer_running = True
            self.session_start_time = time.time()
            self.session_elapsed_time = 0  # Reset elapsed time on new activation
            self.last_motion_time = datetime.now()  # Set initial motion time
            self.display_lcd("Welcome! Sensors Active", duration=3)
            print("System activated.")
        else:
            self.last_motion_time = datetime.now()  # Update last motion time
            print("Motion detected. Idle Timer Reset.")

    def rotate_default_message(self, data):
        """Cycles through default sensor reading displays on LCD.
        Args:
            data: Dictionary of current sensor readings"""
        messages = [
            f"Temp: {data['temperature_c']:.1f}",
            f"Humidity: {data['humidity']}",
            f"Lux: {data['lux']:.1f}"
        ]
        self.display_lcd(messages[self.default_cycle_index], duration=2)
        self.default_cycle_index = (self.default_cycle_index + 1) % len(messages)

    def idle_animation(self):
        """Displays sleeping animation on LCD when system is inactive"""
        while not self.active_mode:
            for dots in range(1, 4):
                self.display_lcd(f"Sleeping{'.' * dots}")
                if self.active_mode:  # Break out if system activates
                    break

    def display_session_summary(self):
        """Shows session statistics on LCD when session ends:
        - Total active time
        - Average temperature
        - Average humidity
        - Average light level"""
        self.display_lcd("Study Session Summary", duration=3)
        minutes, seconds = divmod(self.total_active_time, 60)
        self.display_lcd(f"Total Time: {minutes} min {seconds} sec", duration=3)

        if self.session_data["readings_count"] > 0:
            avg_temp = self.session_data["temp_total"] / self.session_data["readings_count"]
            avg_hum = self.session_data["hum_total"] / self.session_data["readings_count"]
            avg_lux = self.session_data["lux_total"] / self.session_data["readings_count"]
            self.display_lcd(f"Temp Avg: {avg_temp:.1f}", duration=3)
            self.display_lcd(f"Humidity Avg: {avg_hum:.1f}", duration=3)
            self.display_lcd(f"Lux Avg: {avg_lux:.1f}", duration=3)
        self.display_lcd("Goodbye!", duration=3)

    def get_current_reading(self):
        """Return the current sensor data for GUI."""
        return self.current_reading
    def get_current_avgs(self):
        """Return the current sensor data for GUI."""
        return self.current_avgs
    def get_new_data_status(self):
        """Return the new data status for GUI."""
        if self.new_data == True:
            self.new_data = False
            return True
        else:
            return self.new_data
        
    def update_clock(self):
        """Updates the clock every second."""
        now = datetime.now().strftime('%I:%M:%S %p')
        return now

    def update_timer(self):
        """Updates the session timer accounting for breaks"""
        if not self.timer_running:
            return 0
        
        current_time = time.time()
        if self.session_start_time is None:
            return 0
            
        elapsed = current_time - self.session_start_time - self.total_break_time
        return max(0, elapsed)

    def start_break(self):
        """Start a break period"""
        self.break_mode = True
        self.break_start_time = time.time()
        self.current_reading["break_mode"] = True
        self.last_motion_time = datetime.now()
        self.display_lcd("Break Started!", duration=2)

    def end_break(self):
        """End a break period"""
        self.break_mode = False
        self.current_reading["break_mode"] = False
        if self.break_start_time:
            self.total_break_time += time.time() - self.break_start_time
        self.break_start_time = None
        self.last_motion_time = datetime.now()
        self.display_lcd("Break Ended!", duration=2)

    def is_on_break(self):
        """Return current break status"""
        return self.break_mode

    def reset_session_data(self):
        """Resets all session statistics and state variables:
        - Clears averages and totals
        - Resets timers
        - Clears current readings"""
        # Reset session statistics
        self.session_data = {"temp_total": 0, "hum_total": 0, "lux_total": 0, "readings_count": 0}
        
        # Reset current readings
        self.current_reading = {"temperature_c": None, "humidity": None, "lux": None, "break_mode": False}
        
        # Reset averages
        self.current_avgs = {"temperature_c": None, "humidity": None, "lux": None}
        
        # Reset timer data
        self.session_elapsed_time = 0
        self.session_start_time = None
        self.total_break_time = 0
        
        # Reset new data flag
        self.new_data = False

    def run(self):
        """Main operation loop:
        - Monitors sensors
        - Updates database
        - Handles breaks
        - Manages active/idle states
        - Provides environmental suggestions"""
        try:
            while True:
                if self.active_mode:
                    if not self.break_mode:  # Only read sensors when not on break
                        if time.time() - self.last_sensor_read_time >= 5:
                            try:
                                temperature_c = self.dhtDevice.temperature
                                humidity = self.dhtDevice.humidity
                            except RuntimeError as error:
                                print(f"DHT11 error: {error.args[0]}")
                                temperature_c = humidity = None

                            try:
                                raw_value = self.read_adc(0)
                                voltage = raw_value * 3.3 / 255
                                lux = voltage * (1000 / 3.3)
                            except Exception as e:
                                print(f"Light sensor error: {e}")
                                lux = None

                            if temperature_c is not None and humidity is not None and lux is not None:
                                # Update current sensor data for GUI
                                self.current_reading = {
                                    "temperature_c": temperature_c,
                                    "humidity": humidity,
                                    "lux": lux
                                }

                                # Log sensor data to the console
                                print(f"Sensor Data - Temp: {temperature_c:.1f}C, Humidity: {humidity}%, Lux: {lux:.1f}")
                                try:
                                    cursor = self.conn.cursor()
                                    sql = ("INSERT INTO readings (time, temperature_c, humidity, lux) "
                                           "VALUES (%s, %s, %s, %s)")
                                    val = (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                           temperature_c, humidity, lux)
                                    cursor.execute(sql, val)
                                    self.conn.commit()
                                    
                                    # Update session statistics
                                    self.session_data["temp_total"] += temperature_c
                                    self.session_data["hum_total"] += humidity
                                    self.session_data["lux_total"] += lux
                                    self.session_data["readings_count"] += 1

                                    avg_temp = round(self.session_data["temp_total"] / self.session_data["readings_count"], 1)
                                    avg_hum = round(self.session_data["hum_total"] / self.session_data["readings_count"], 1)
                                    avg_lux = round(self.session_data["lux_total"] / self.session_data["readings_count"], 1)
                                    self.current_avgs = {
                                        "temperature_c": avg_temp,
                                        "humidity": avg_hum,
                                        "lux": avg_lux
                                    }

                                    # Increment total active time by the data collection interval
                                    self.total_active_time += 5

                                    # Display environmental suggestions
                                    suggestions = self.get_suggestions(temperature_c, humidity, lux)
                                    for suggestion in suggestions:
                                        self.display_lcd(suggestion, duration=2)

                                    self.new_data = True

                                except mysql.connector.Error as e:
                                    print(f"Database error: {e}")
                                finally:
                                    cursor.close()

                            self.last_sensor_read_time = time.time()
                    else:
                        # During break, display message once and sleep
                        if self.current_lcd_message != "On Break Relax...":
                            self.display_lcd("On Break Relax...", duration=2)
                        time.sleep(1)
                        self.new_data = False
                        continue  # Skip the rest of the loop during break

                    # Only do these if not in break mode
                    if not self.break_mode:
                        latest_data = self.fetch_latest_data()
                        self.rotate_default_message(latest_data)

                    current_time = datetime.now()
                    if self.start_time is None:
                        self.start_time = current_time


                    # Check for inactivity
                    if self.last_motion_time and (current_time - self.last_motion_time).seconds > 20:
                        print("No motion detected for 20 seconds. Going idle.")
                        self.reset_session_data()  # Keep only one call
                        self.new_data = True
                        self.active_mode = False
                        self.timer_running = False
                        self.display_session_summary()
                        self.last_motion_time = None

                else:
                    self.idle_animation()

        except KeyboardInterrupt:
            print("\nExiting program.")
        finally:
            try:
                self.dhtDevice.exit()
                self.pir.close()
                self.bus.close()
                self.conn.close()
            except Exception as e:
                print(f"Error during cleanup: {e}")
            self.lcd.clear()
            print("Resources released. Program terminated.")

if __name__ == "__main__":
    study_helper = StudyHelper()
    study_helper.run()
