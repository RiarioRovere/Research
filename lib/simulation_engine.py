import random
from typing import Optional, Callable
from enum import Enum
from collections import defaultdict
import logging


class RadioChannel:
    def __init__(self):
        self.time = 0
        self.data = []

    def transmit(self, locket_id: int):
        self.data.append(locket_id)

    def receive(self) -> Optional[str]:
        if len(self.data) != 1:
            return None

        return self.data[0]

    def is_free(self) -> bool:
        return len(self.data) == 0

    def tick(self):
        self.data = []
        self.time += 1

    def set_time(self, time):
        self.time = time
        self.data = []


rc = RadioChannel()


class EState(Enum):
    TX = 0
    RX = 1
    SLEEP = 2
    WAKING_UP = 3
    OFF = 4
    ON = 5
    CHANNEL_CHECK = 6


SUPERCYCLE_LENGTH = 1 * 10 ** 6
RC_CHANNEL_CHECK_TIME = 300
TX_TIME = 1


class Locket:
    def __init__(self, locket_id, turn_on_at):
        self.relative_time = 0
        self.absolute_time = 0
        self.turn_on_at = turn_on_at

        self.locket_id = locket_id
        self.state: EState = EState.OFF
        self.state_timer = 0

        self.sleep_timer = 0
        self.tx_freq = 5
        self.timeslot_size = SUPERCYCLE_LENGTH / self.tx_freq
        self.rx_state: defaultdict[str, int] = defaultdict(int)
        self.received: list[str] = []

    def sleep(self, mcs):
        self.sleep_timer = mcs
        self.set_state(EState.SLEEP)

    def is_channel_free(self):
        rc.is_free()

    def set_state(self, state: EState):
        logging.info(f"[{self.locket_id}] enter {state} state at {self.relative_time}")
        self.state = state
        self.rx_state.clear()
        self.state_timer = 0

    def get_timeslot(self):
        return self.relative_time // self.timeslot_size

    def tick(self):
        self.absolute_time += 1
        if self.state != EState.OFF:
            self.relative_time += 1
            self.relative_time %= SUPERCYCLE_LENGTH
            self.state_timer += 1

        if self.state == EState.OFF:
            if self.absolute_time == self.turn_on_at:
                self.set_state(EState.WAKING_UP)
        elif self.state == EState.SLEEP:
            if self.state_timer == self.sleep_timer:
                self.set_state(EState.WAKING_UP)
        elif self.state == EState.WAKING_UP:
            if self.state_timer == 240:
                if self.get_timeslot() == 0:
                    self.set_state(EState.RX)
                else:
                    self.set_state(EState.CHANNEL_CHECK)

        elif self.state == EState.TX:
            rc.transmit(self.locket_id)
            if self.state_timer == TX_TIME:
                sleep_before = self._sleep_before_next_timeslot()
                self.sleep(sleep_before)

        elif self.state == EState.RX:
            packet = rc.receive()
            if self.state_timer == self.timeslot_size:
                self.set_state(EState.WAKING_UP)
            if packet is not None:
                self.rx_state[packet] += 1
                if self.rx_state[packet] == TX_TIME:
                    self.received.append(packet)

        elif self.state == EState.ON:
            pass
        elif self.state == EState.CHANNEL_CHECK:
            if not rc.is_free():
                self.sleep(TX_TIME)
            if self.state_timer == RC_CHANNEL_CHECK_TIME:
                self.set_state(EState.TX)

    def _sleep_before_next_timeslot(self):
        self.sleep(self._next_timeslot_start() - self.relative_time)

    def _next_timeslot_start(self):
        cur_ts = self.relative_time // self.timeslot_size
        return (cur_ts + 1) * self.timeslot_size



class Engine:
    def __init__(self, lockets: list[Locket]):
        self.lockets: list[Locket] = lockets
        self.time = 0

    def process(self, super_cycles):
        for i in range(super_cycles):
            self.super_cycle()

    def super_cycle(self):
        for i in range(SUPERCYCLE_LENGTH):
            self.tick()

    def tick(self):
        self.time += 1

        tx_lockets = self._filter_by_state(EState.TX)
        for locket in tx_lockets:
            locket.tick()
            assert locket.absolute_time == self.time, f'{locket.absolute_time} {self.time}'

        for locket in self.lockets:
            if locket not in tx_lockets and locket.state != EState.TX:
                locket.tick()
                assert locket.absolute_time == self.time, f'{locket.absolute_time} {self.time}'

    def _filter_by_state(self, state: EState):
        return filter(lambda l: l.state == state, self.lockets)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    LOCKET_CNT = 2
    lockets = []
    for i in range(LOCKET_CNT):
        wakeup_time = 1 if i == 0 else 2 * 10 ** 6
        lockets.append(Locket(i, wakeup_time))

    main_locket = lockets[0]

    engine = Engine(lockets)
    engine.process(2)
    print(main_locket.received)






































