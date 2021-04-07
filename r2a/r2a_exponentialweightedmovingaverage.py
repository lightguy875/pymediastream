from r2a.ir2a import IR2A
from player.parser import *
import time
from pandas import DataFrame
from pandas import *

class R2A_ExponentialWeightedMovingAverage(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs = []
        self.request_time = 0
        self.qi = []
        self.smooth = []

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):

        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / (1.5*t))

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        df = DataFrame (self.throughputs,columns=['throughputs'])
        self.smooth = df.ewm(alpha=0.5).mean()
        self.smooth = df.values.tolist()

        selected_qi = self.qi[0]
        for i in self.qi:
            if self.smooth[-1][-1] > i:
                selected_qi = i

        msg.add_quality_id(selected_qi)
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / (1.5*t))
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass