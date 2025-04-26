"""
SWE-410: Smart Study Desk Assistant
Authors: Fernando Godinez
Due Date: 3/2/2025
This is my own work.
"""

import unittest
import time
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch


# Dummy classes to override hardware access in StudyHelper.
class DummyMotionSensor:
    def __init__(self, *args, **kwargs):
        pass
    def wait_for_no_motion(self):
        pass
    def close(self):
        pass

class DummyLCD:
    def __init__(self, *args, **kwargs):
        pass
    def clear(self):
        pass
    def write_string(self, s):
        pass

# Patch the MotionSensor and CharLCD in the StudyHelper module.
@patch('StudyHelper.MotionSensor', new=DummyMotionSensor)
@patch('StudyHelper.CharLCD', new=DummyLCD)
class TestStudyHelper(unittest.TestCase):

    def setUp(self):
        # Import StudyHelper after the patches are applied.
        from StudyHelper import StudyHelper
        self.sh = StudyHelper()
        # Override display_lcd so it doesn't actually sleep.
        self.sh.display_lcd = lambda message, duration=0: None

    def tearDown(self):
        try:
            self.sh.dhtDevice.exit()
            self.sh.pir.close()
            self.sh.bus.close()
            self.sh.conn.close()
        except Exception:
            pass

    def test_get_suggestions(self):
        # When conditions are normal, no suggestions.
        suggestions = self.sh.get_suggestions(25, 50, 500)
        self.assertEqual(suggestions, [])
        # High temperature should suggest turning on the fan.
        suggestions = self.sh.get_suggestions(35, 50, 500)
        self.assertIn("Turn on the fan", suggestions)
        # Low temperature should suggest turning on the heater.
        suggestions = self.sh.get_suggestions(15, 50, 500)
        self.assertIn("Turn on the heater", suggestions)
        # Low humidity should suggest turning on a humidifier.
        suggestions = self.sh.get_suggestions(25, 0, 500)
        self.assertIn("Turn on a humidifier", suggestions)
        # High humidity should suggest turning off a humidifier.
        suggestions = self.sh.get_suggestions(25, 80, 500)
        self.assertIn("Turn off a humidifier", suggestions)
        # Low light should suggest turning on a lamp.
        suggestions = self.sh.get_suggestions(25, 50, 50)
        self.assertIn("Turn on a lamp", suggestions)
        # High light should suggest reducing lighting.
        suggestions = self.sh.get_suggestions(25, 50, 1500)
        self.assertIn("Reduce lighting", suggestions)

    def test_update_clock(self):
        clock_str = self.sh.update_clock()
        self.assertIsInstance(clock_str, str)
        # Expect a format like "12:34:56 PM" (at least 11 characters).
        self.assertTrue(len(clock_str) == 11)

    def test_update_timer_without_session_start(self):
        self.sh.session_start_time = None
        elapsed = self.sh.update_timer()
        self.assertEqual(elapsed, 0)

    def test_reset_session_data(self):
        # Set dummy values.
        self.sh.session_data = {"temp_total": 100, "hum_total": 100, "lux_total": 100, "readings_count": 10}
        self.sh.current_reading = {"temperature_c": 25, "humidity": 50, "lux": 300, "break_mode": True}
        self.sh.current_avgs = {"temperature_c": 25, "humidity": 50, "lux": 300}
        self.sh.session_start_time = time.time()
        self.sh.total_break_time = 20

        self.sh.reset_session_data()
        self.assertEqual(self.sh.session_data, {"temp_total": 0, "hum_total": 0, "lux_total": 0, "readings_count": 0})
        self.assertEqual(self.sh.current_reading, {"temperature_c": None, "humidity": None, "lux": None, "break_mode": False})
        self.assertEqual(self.sh.current_avgs, {"temperature_c": None, "humidity": None, "lux": None})
        self.assertIsNone(self.sh.session_start_time)
        self.assertEqual(self.sh.total_break_time, 0)

    def test_motion_detected_activation(self):
        self.sh.active_mode = False
        self.sh.session_start_time = None
        self.sh.motion_detected()
        self.assertTrue(self.sh.active_mode)
        self.assertIsNotNone(self.sh.session_start_time)

    def test_break_mode(self):
        self.sh.break_mode = False
        self.sh.start_break()
        self.assertTrue(self.sh.break_mode)
        self.sh.end_break()
        self.assertFalse(self.sh.break_mode)

    def test_new_data_flag(self):
        self.sh.new_data = True
        status = self.sh.get_new_data_status()
        self.assertTrue(status)
        # The flag should now be reset.
        self.assertFalse(self.sh.get_new_data_status())

    def test_rotate_default_message(self):
        dummy_data = {"temperature_c": 20, "humidity": 50, "lux": 300}
        # Override display_lcd to capture the message instead of printing.
        captured = []
        self.sh.display_lcd = lambda message, duration=0: captured.append(message)
        self.sh.default_cycle_index = 0
        self.sh.rotate_default_message(dummy_data)
        self.assertGreater(len(captured), 0)
        # Verify that the first message matches the expected format.
        self.assertIn("Temp:", captured[0])

    def test_timer_updates(self):
        self.sh.timer_running = True # Start the timer.
        self.sh.session_start_time = time.time() - 10  # 10 seconds ago
        elapsed = self.sh.update_timer()
        self.assertAlmostEqual(elapsed, 10, delta=1)






if __name__ == '__main__':
    unittest.main()
