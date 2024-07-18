import ctypes
import time
import math
from sdl2 import *

import cantools
import can

class CanMessageFactory:
    def __init__(self):
        cans_dbc_path = 'can_common/dbc/can_s.dbc'
        canv_dbc_path = 'can_common/dbc/can_v.dbc'

        self.can_s_db = cantools.database.load_file(cans_dbc_path)
        self.can_v_db = cantools.database.load_file(canv_dbc_path)

        self.button_inputs_msg = self.can_s_db.get_message_by_name(
            "STEERING_WHEEL_ButtonInputs"
        )
        self.simulator_input_msg = self.can_v_db.get_message_by_name(
            "EXTERNAL_SimulatorInput"
        )


    def generate_simulator_input(self, pps: float, brake_force: float, angle: float) -> can.Message:
        data = self.simulator_input_msg.encode(
            {
                "brake_force": brake_force,
                "pps": pps,
                "delta_v": angle,
            }
        )
        return can.Message(
            arbitration_id=self.simulator_input_msg.frame_id,
            data=data,
            is_extended_id=False,
        )


    def generate_sw_button(self, states: list[bool]) -> can.Message:
        assert len(states) == 6

        buttons_val = 0
        for i, s in enumerate(states):
            buttons_val |= s << i

        data = self.button_inputs_msg.encode(
            {
                "buttons": buttons_val,
                "rotary_switch": 0,
                "rotary_encoder_position": 0,
            }
        )
        return can.Message(
            arbitration_id=self.button_inputs_msg.frame_id,
            data=data,
            is_extended_id=False,
        )

MSG_FACTORY = CanMessageFactory()

class Joystick:
    def __init__(self):
        SDL_Init(SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)
        self._trigger_left = 0
        self._trigger_right = 0
        self._left_x = 0
        self._left_y = 0
        self._button_events = []
        self._button_states = [False] * 6

    def connect(self):
        event = SDL_Event()
        while SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == SDL_CONTROLLERDEVICEADDED:
                self.device = SDL_GameControllerOpen(event.cdevice.which)
                self.guid = SDL_JoystickGetDeviceGUID(event.cdevice.which)
                self.jdevice = event.jdevice
                return True
        return False

    def update(self):
        event = SDL_Event()
        while SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == SDL_CONTROLLERAXISMOTION:
                value = SDL_GameControllerGetAxis(self.device, event.caxis.axis)
                if event.caxis.axis == SDL_CONTROLLER_AXIS_TRIGGERLEFT:
                    self._trigger_left = value / (2**15-1)
                elif event.caxis.axis == SDL_CONTROLLER_AXIS_TRIGGERRIGHT:
                    self._trigger_right = value / (2**15-1)
                elif event.caxis.axis == SDL_CONTROLLER_AXIS_LEFTX:
                    self._left_x = 2*((value + 2**15) / (2**16-1) - 0.5)
                elif event.caxis.axis == SDL_CONTROLLER_AXIS_LEFTY:
                    self._left_y = 2 *((value + 2**15) / (2**16-1) - 0.5)
            elif event.type == SDL_CONTROLLERBUTTONDOWN or event.type == SDL_CONTROLLERBUTTONUP:
                value = SDL_GameControllerGetButton(self.device, event.cbutton.button)
                self._button_events.append((event.cbutton.button, value,))


    def trigger_left(self) -> float:
        return self._trigger_left

    def trigger_right(self) -> float:
        return self._trigger_right

    def axis_left(self) -> tuple[float]:
        return (self._left_x, self._left_y)

    def get_button_event(self) -> can.Message | None:
        if len(self._button_events) > 0:
            button_num, state = self._button_events[0]

            if button_num == SDL_CONTROLLER_BUTTON_A:
                self._button_states[0] = bool(state)
            elif button_num == SDL_CONTROLLER_BUTTON_B:
                self._button_states[1] = bool(state)
            elif button_num == SDL_CONTROLLER_BUTTON_X:
                self._button_states[6] = bool(state)

            self._button_events = self._button_events[1:]

            return MSG_FACTORY.generate_sw_button(self._button_states)

        return None


if __name__ == "__main__":
    joystick = Joystick()
    with can.Bus("vcanv", interface="socketcan") as canv:
        with can.Bus("vcans", interface="socketcan") as cans:
            while True:
                if joystick.connect():
                    print("Controller detected")
                    break
                time.sleep(0.1)

            while True:
                joystick.update()
                pps = joystick.trigger_left()
                brake_pressure = joystick.trigger_right() * 400
                delta_v = joystick.axis_left()[0] * math.pi
                sim_input = MSG_FACTORY.generate_simulator_input(pps, brake_pressure, delta_v)
                canv.send(sim_input)
                button_msg = joystick.get_button_event()
                if button_msg is not None:
                    cans.send(button_msg)

                time.sleep(0.1)

