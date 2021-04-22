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
        self.smooth = [0]
        self.estimateband = [0]
        self.k = 0.14
        self.w = 50000
        self.alfa = 0.2
        self.t = 0
        self.deltaup = 0
        self.deltadown = 0
        self.e = 0.15
        self.quality = [0]
        self.buffer = [] #lista para o buffer
        self.buffer_min = 40
        self.Tf = 1 #período de espera do próximo segmento
        self.beta = 0.15 #ganho do feedback de controle do buffer


    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        self.t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / self.t)
        self.estimateband.append((self.k*(self.w*10**6 - max(0,(self.estimateband[-1] - self.throughputs[-1] + self.w*10**6))))*self.Tf + self.estimateband[-1])
        self.send_up(msg)
        
    def handle_segment_size_request(self, msg):

        self.request_time = time.perf_counter()
        df = DataFrame (self.estimateband,columns=['throughputs'])
        df.ewm(alpha=0.5).mean()
        valor = df.values.tolist()[-1][-1]
        self.smooth.append((-self.alfa*( valor - self.estimateband[-1])*self.Tf) + valor)

        self.deltaup = self.e * self.smooth[-1]
        qualityup = self.smooth[-1] - self.deltaup
        qualitydown = self.smooth[-1] - self.deltadown

        if self.quality[-1] < qualityup:
            self.quality.append(qualityup)
        elif qualityup <= self.quality[-1] and self.quality[-1] <= qualitydown:
            self.quality.append(self.quality[-1])
        else:
            self.quality.append(qualitydown)

        selected_qi = self.qi[0]
        for i in self.qi:
            if self.quality[-1] > i:
                selected_qi = i

        msg.add_quality_id(selected_qi)
        self.send_down(msg)


        varial = 0
        #pego somente após o buffer sair de índice com significado
        if len(list(self.whiteboard.get_playback_buffer_size()))>2:
            varial = list( self.whiteboard.get_playback_buffer_size()) #pego o valor do meu buffer
            self.buffer.append(float(varial[-1][1]))
            T_bar = ((selected_qi * 1) / self.smooth[-1]) + self.beta*(self.buffer[-1] - self.buffer_min)
            T_tio = self.t #somente definindo para ficar igual a equaçao 1 do artigo
        
            self.Tf = max(T_bar, T_tio)

    def handle_segment_size_response(self, msg):
        self.t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / self.t)  
        self.estimateband.append((self.k*(self.w - max(0,(self.estimateband[-1] - self.throughputs[-1] + self.w))))*self.Tf + self.estimateband[-1])

        
       
        self.send_up(msg)
    #            print(self.throughputs[-1])
    #    print(self.estimateband[-1])


    def initialize(self):
        pass

    def finalization(self):
        pass