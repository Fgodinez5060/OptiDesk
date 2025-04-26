"""
SWE-410: Smart Study Desk Assistant
Authors: Fernando Godinez
Due Date: 3/2/2025
This is my own work.
"""

import tkinter as tk
from tkinter import ttk
import time
import threading
from datetime import datetime
from StudyHelper import StudyHelper

class StudyHelperApp:
    """Main GUI application class for Study Helper. Handles all user interface elements
    and interactions with the StudyHelper backend."""

    def __init__(self, root):
        """Initialize the GUI application.
        Args:
            root: The main Tkinter window"""
        self.root = root
        self.root.title("Study Helper")
        self.root.geometry("700x550")
        self.enable_dark_mode()
        
        # Configure Grid Columns
        self.root.columnconfigure(0, weight=1)  # Center elements properly
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(6, weight=1)  # Push bottom elements down

        # Login Screen
        self.login_frame = tk.Frame(root, bg='#2E2E2E')
        self.login_frame.pack(expand=True)
        
        self.name_label = tk.Label(self.login_frame, text="Enter Your Name:", fg='white', bg='#2E2E2E')
        self.name_label.pack(pady=5)
        
        self.name_entry = tk.Entry(self.login_frame, bg='#555', fg='white', insertbackground='white')
        self.name_entry.pack(pady=5)
        
        self.submit_button = tk.Button(self.login_frame, text="Submit", command=self.start_app, bg='#444', fg='white', activebackground='#666')
        self.submit_button.pack(pady=5)
        
        self.timer_paused = False  # Add this new variable

    def enable_dark_mode(self):
        """Applies dark theme colors to the application window"""
        self.root.configure(bg='#2E2E2E')
    
    def start_app(self):
        """Initializes the main application after login:
        - Creates StudyHelper instance
        - Starts sensor monitoring thread
        - Sets up all GUI elements
        - Initializes update loops"""
        # Connect to the StudyHelper class
        self.SH = StudyHelper()

        # Start the StudyHelper thread
        thread = threading.Thread(target=self.SH.run, daemon=True)
        thread.start()
    
        """Initialize the main application GUI after login."""
        self.user_name = self.name_entry.get() or "Guest"
        
        self.login_frame.destroy()

        # Top Frame (For Progress Bar & Clock)
        self.top_frame = tk.Frame(self.root, bg='#2E2E2E')
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10)
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

        self.get_clock()  # Start clock updates

        # Data Frame (Now with 3 values)
        self.data_frame = tk.LabelFrame(self.root, text="Environmental Data", 
                                        font=("Arial", 10, "bold"), fg="white", bg='#444', 
                                        labelanchor="n", bd=2, relief=tk.GROOVE)
        self.data_frame.grid(row=2, column=0, columnspan=2, pady=25, padx=10, sticky='nsew')

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

        # Text Display Frame
        self.text_display_frame = tk.LabelFrame(self.root, text="Status", 
                                              font=("Arial", 10, "bold"),
                                              fg="white", bg='#444',
                                              labelanchor="n", bd=2,
                                              relief=tk.GROOVE)
        self.text_display_frame.grid(row=3, column=0, columnspan=2, pady=10, padx=10, sticky='nsew')

        # Status Text Label
        self.status_text = tk.Label(self.text_display_frame,
                                  text="Loading Study Helper...",
                                  font=("Arial", 12),
                                  fg='white', bg='#333',
                                  wraplength=400)  # Adjust wraplength as needed
        self.status_text.pack(padx=5, pady=5, fill='both')

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

        # Start the progress bar and data update
        self.update_timer()
        self.update_progress()
        self.update_data()
    
    def get_clock(self):
        """Updates the clock display every second with current time from StudyHelper"""
        now = self.SH.update_clock()
        self.clock_label.config(text=now)
        self.root.after(1000, self.get_clock)

    def update_timer(self):
        """Updates the session timer display every second.
        Pauses during breaks and shows elapsed study time."""
        if not self.break_active:  # Only update if not on break
            elapsed = self.SH.update_timer()
            minutes, seconds = divmod(int(elapsed), 60)
            self.timer_label.config(text=f"Elapsed Time: {minutes:02}:{seconds:02}")
        self.root.after(1000, self.update_timer)
    
    def update_progress(self):
        """Updates the break timer progress bar every 500ms.
        Triggers a break when progress reaches 100%.
        Only updates when system is active and not on break."""
        if not self.break_active and self.running and self.SH.active_mode:
            self.progress_value += 1
            if self.progress_value > 100:
                self.start_break()
                return
        self.progress["value"] = self.progress_value

        if self.running:
            self.root.after(500, self.update_progress)
    
    def update_data(self):
        """Updates all environmental sensor displays every second.
        - Shows LCD messages from Pi
        - Updates temperature, humidity, and light readings
        - Updates average values
        Only updates sensor data when not on break."""
        if self.running:
            # Always get LCD message from Pi, even during breaks
            lcd_message = self.SH.get_lcd_message()
            if lcd_message:
                self.status_text.config(text=lcd_message)
                
            if not self.break_active and self.SH.get_new_data_status():
                # Get current readings
                data_values = self.SH.get_current_reading()
                data_avgs = self.SH.get_current_avgs()
                
                # Update sensor labels
                temp = f"{data_values.get('temperature_c', '--'):.1f}" if data_values.get('temperature_c') is not None else "--"
                humidity = f"{data_values.get('humidity', '--'):.1f}" if data_values.get('humidity') is not None else "--"
                lux = f"{data_values.get('lux', '--'):.1f}" if data_values.get('lux') is not None else "--"

                avg_temp = f"{data_avgs.get('temperature_c', '--'):.1f}" if data_avgs.get('temperature_c') is not None else "--"
                avg_humidity = f"{data_avgs.get('humidity', '--'):.1f}" if data_avgs.get('humidity') is not None else "--"
                avg_lux = f"{data_avgs.get('lux', '--'):.1f}" if data_avgs.get('lux') is not None else "--"

                # Update Labels with values from pi
                self.temp_label.config(text=f"Temperature: {temp}°C")
                self.humidity_label.config(text=f"Humidity: {humidity}%")
                self.lux_label.config(text=f"Lux: {lux} lx")

                self.temp_avg_label.config(text=f"Avg. Temp: {avg_temp}°C")
                self.humidity_avg_label.config(text=f"Avg. Hum: {avg_humidity}%")
                self.lux_avg_label.config(text=f"Avg. Lux: {avg_lux} lx")

        self.root.after(1000, self.update_data)

    
    def start_break(self):
        """Initiates a break period:
        - Pauses data updates
        - Clears sensor displays
        - Starts break timer
        - Updates Pi break state"""
        if not self.break_active:
            self.break_active = True
            # Clear displays immediately
            self.break_label.config(text="Break in Progress")
            self.clear_sensor_displays()
            # Start break on Pi in separate thread
            threading.Thread(target=self.SH.start_break, daemon=True).start()
            threading.Thread(target=self.break_timer, daemon=True).start()

    def break_timer(self):
        """Handles break duration timing using Tkinter's after method.
        Currently set to 5 seconds for testing."""
        # Use root.after instead of sleep
        self.root.after(5000, self.end_break)  # 5000ms = 5 seconds

    def end_break(self):
        """Handles end of break period:
        - Resumes data updates
        - Resets progress bar
        - Updates Pi break state"""
        self.break_active = False
        threading.Thread(target=self.SH.end_break, daemon=True).start()
        self.break_label.config(text="")
        self.progress_value = 0
        self.progress["value"] = 0
        self.update_progress()

    def clear_sensor_displays(self):
        """Clears all sensor displays by setting them to default values"""
        self.temp_label.config(text="Temperature: --°C")
        self.humidity_label.config(text="Humidity: --%")
        self.lux_label.config(text="Lux: -- lx")
        self.temp_avg_label.config(text="Avg. Temp: --°C")
        self.humidity_avg_label.config(text="Avg. Hum: --%")
        self.lux_avg_label.config(text="Avg. Lux: -- lx")

    def on_close(self):
        """Handles application shutdown:
        - Cancels all scheduled updates
        - Stops sensor monitoring
        - Closes database connection
        - Destroys main window"""
        self.running = False  # Stop update loops
        
        # Cancel all scheduled updates
        if hasattr(self, 'root'):
            self.root.after_cancel(self.root.after(0, lambda: None))  # Cancel all pending after() calls
        
        # Clean up StudyHelper resources
        if hasattr(self, 'SH'):
            self.SH.display_session_summary()
        
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyHelperApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
