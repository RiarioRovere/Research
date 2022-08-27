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
TX_TIME = 2 * 10 ** 3


class Stat:
    def __init__(self):
        self.received = 0
        self.busy_channel = 0

    def reset(self):
        self.received = 0
        self.busy_channel = 0

    def __str__(self):
        return f'''
            received = {self.received}
            busy_channel = {self.busy_channel}
        '''


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
        self.timeslot_size = SUPERCYCLE_LENGTH // self.tx_freq
        self.rx_state: defaultdict[str, int] = defaultdict(int)
        self.received: set[str] = set()
        self.stat: Stat = Stat()

    def sleep(self, mcs):
        self.sleep_timer = mcs
        self.set_state(EState.SLEEP)

    def is_channel_free(self):
        rc.is_free()

    def set_state(self, state: EState):
        logging.info(f"[{self.locket_id}] {self.state} -> {state} state at {self.absolute_time}")
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
                self._sleep_before_next_timeslot()

        elif self.state == EState.RX:
            packet = rc.receive()
            if self.state_timer == self.timeslot_size:
                self.set_state(EState.WAKING_UP)
            if packet is not None:
                self.rx_state[packet] += 1
                if self.rx_state[packet] == TX_TIME:
                    self.received.add(packet)

        elif self.state == EState.CHANNEL_CHECK:
            # if not rc.is_free():
            #     self.stat.busy_channel += 1
            #     self.sleep(TX_TIME)
            if self.state_timer == RC_CHANNEL_CHECK_TIME:
                self.set_state(EState.TX)

    def reset_stat(self):
        self.stat.reset()
        self.received = set()

    def _sleep_before_next_timeslot(self):
        self.sleep(self._next_timeslot_start() - self.relative_time)

    def _next_timeslot_start(self):
        cur_ts = self.relative_time // self.timeslot_size
        return (cur_ts + 1) * self.timeslot_size

    def __eq__(self, other):
        return self.locket_id == other.locket_id

    def __hash__(self):
        return self.locket_id


class Engine:
    def __init__(self, lockets: list[Locket], rc: RadioChannel):
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
        rc.tick()
        assert rc.time == self.time, \
            f'abs_time = {self.time} rc_time = {rc.time}'

        tx_lockets = self._filter_by_state(EState.TX)
        for locket in tx_lockets:
            locket.tick()
            assert locket.absolute_time == self.time, \
                f'{locket.locket_id}: abs_time = {self.time} locket_time = {locket.absolute_time}'

        if (self.lockets[0].state == EState.RX):
            logging.error(f"RX -> {self.lockets[1].state}")

        for locket in self.lockets:
            if locket not in tx_lockets:
                locket.tick()
                assert locket.absolute_time == self.time, \
                    f'{locket.locket_id}: abs_time = {self.time} locket_time = {locket.absolute_time}'

    def _filter_by_state(self, state: EState):
        return list(filter(lambda l: l.state == state, self.lockets))


if __name__ == '__main__':
    logging.basicConfig(level=logging.CRITICAL)

    rc = RadioChannel()

    LOCKET_CNT = 5
    lockets = []
    for i in range(LOCKET_CNT):
        wakeup_time = 1 if i == 0 else SUPERCYCLE_LENGTH // 2
        lockets.append(Locket(i, wakeup_time))

    main_locket = lockets[0]

    engine = Engine(lockets, rc)

    for i in range(3):
        print(f'Iteration №{i}')
        engine.process(1)
        for locket in lockets:
            print(locket.locket_id)
            print(locket.stat)
            print(locket.received)





































