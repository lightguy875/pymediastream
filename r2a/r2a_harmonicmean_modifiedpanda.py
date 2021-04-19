from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import harmonic_mean

class R2A_HarmonicMean_ModifiedPanda(IR2A):


    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs = []
        self.request_time = 0
        self.qi = []
        self.smooth = [0]
        self.estimateband = [0]
        self.k = 0.56
        self.w = 0.3
        self.alfa = 0.2
        self.t = 0
        self.e = 0.15
        self.quality = [0]

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        self.t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / self.t)
        self.estimateband.append((self.k*(self.w - max(0,(self.estimateband[-1]-self.throughputs[-1] + self.w))*self.t) + self.throughputs[-1])) #modo PANDA para estimar a banda, porém utilizando throughput na última soma

        self.send_up(msg)

    def handle_segment_size_request(self, msg):

        self.request_time = time.perf_counter()

        if self.estimateband[-1] > 0 and self.estimateband[-2] > 0 and self.estimateband[-3] > 0 and self.estimateband[-4] > 0 and self.estimateband[-5] > 0:
            valor = harmonic_mean(self.estimateband[-5::]) #média dos últimos 5 números da banda estimada apenas se todos forem positivos

        else:
            valor = harmonic_mean(self.estimateband)
            
        self.smooth.append((-self.alfa*(valor - self.estimateband[-1])*self.t) + valor)

        delta_up = self.e * self.smooth[-1]

        selected_qi_up = self.smooth[-1] - delta_up
        selected_qi_down = self.smooth[-1]

        if self.quality[-1] < selected_qi_up:
            self.quality[-1] = selected_qi_up

        elif selected_qi_up <= self.quality[-1] and self.quality[-1] <= selected_qi_down:
            self.quality[-1] = self.quality[-1]

        else:
            self.quality[-1] = selected_qi_down

        selected_qi = self.qi[0]

        for i in self.qi:
            if self.quality[-1] > i:
                selected_qi = i 

        msg.add_quality_id(selected_qi)
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / self.t)
        self.estimateband.append((self.k*(self.w - max(0,(self.estimateband[-1]-self.throughputs[-1] + self.w))*self.t) + self.throughputs[-1]))

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass