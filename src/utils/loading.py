from queue import Queue
from threading import Event, Thread
from time import sleep
from typing import Callable, Tuple


class loading(Thread):
    signs = ["—", "\\", "|", "/"]
    sign_index: int = 0
    exit_signal: Event
    message_queue: Queue
    already_paused: bool

    def __init__(
        self, message_queue: Queue, is_pause: bool = False, keep_log: bool = False
    ):
        self.exit_signal = Event()
        self.pause_signal = Event()
        self.keep_log = keep_log
        self.already_paused = False
        self.pause(is_pause, True)
        self.message_queue = message_queue
        self.prev_message = (None, False, None)
        Thread.__init__(self=self)

    def stop(self):
        self.pause_signal.set()
        self.exit_signal.set()

    @property
    def is_paused(self):
        return self.pause_signal.is_set()

    def pause(self, is_pause: bool = True, is_init: bool = False):
        if is_pause:
            self.pause_signal.set()
            if not is_init and not self.keep_log:
                print("\033[F\033[1G\033[K", end="\r")
        else:
            self.already_paused = False
            self.pause_signal.clear()

    def print_message(self, message_tuple: Tuple[str, bool, Callable]):

        message, _, callback = message_tuple
        if callback is not None:
            callback(message)
        print(message + " " + self.signs[self.sign_index])
        self.sign_index = (self.sign_index + 1) % len(self.signs)
        sleep(0.5)
        print("\033[F\033[1G\033[K", end="\r")

    def run(self):
        while not self.exit_signal.is_set():
            if self.pause_signal.is_set() and self.already_paused:
                continue
            curr_message = ""
            if self.message_queue.empty():
                curr_message = self.prev_message
            else:
                curr_message = self.message_queue.get()
                if curr_message[1] and self.prev_message[0] is not None:
                    print(self.prev_message[0])
                self.prev_message = curr_message
            if self.prev_message[0] is None:
                continue
            self.print_message(curr_message)
        print(self.prev_message[0])
