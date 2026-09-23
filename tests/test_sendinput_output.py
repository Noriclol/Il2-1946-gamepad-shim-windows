import threading
import unittest

from res.mouse_look import MouseLookState
from res.sendinput_output import mouse_tick_loop, send_relative_mouse_move


class TestSendRelativeMouseMoveNoOp(unittest.TestCase):
    def test_zero_delta_does_not_touch_ctypes_windll(self):
        # Only the zero/zero case is testable off Windows -- any other
        # input would reach ctypes.windll, which doesn't exist here.
        send_relative_mouse_move(0, 0)


class TestMouseTickLoop(unittest.TestCase):
    def test_deflected_stick_produces_repeated_nonzero_moves(self):
        state = MouseLookState()
        state.set(vx=1.0, vy=0.0)
        stop_event = threading.Event()
        calls = []

        def fake_send_move(dx, dy):
            calls.append((dx, dy))
            if len(calls) >= 3:
                stop_event.set()

        # High rate_hz keeps the loop's real time.sleep() calls negligible.
        mouse_tick_loop(state, stop_event, rate_hz=1000, send_move=fake_send_move)

        self.assertEqual(len(calls), 3)
        self.assertTrue(all(dx > 0 and dy == 0 for dx, dy in calls))

    def test_centred_stick_produces_no_moves(self):
        state = MouseLookState()
        stop_event = threading.Event()
        calls = []

        def fake_send_move(dx, dy):
            calls.append((dx, dy))

        # Set the stop flag on the first tick regardless -- a centred
        # stick's dx/dy are always 0, so send_move is still called (the
        # loop doesn't skip the call), just with a zero payload.
        def stopping_send_move(dx, dy):
            fake_send_move(dx, dy)
            stop_event.set()

        mouse_tick_loop(state, stop_event, rate_hz=1000, send_move=stopping_send_move)

        self.assertEqual(calls, [(0, 0)])


if __name__ == "__main__":
    unittest.main()
