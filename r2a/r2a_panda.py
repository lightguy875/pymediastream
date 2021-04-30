from r2a.ir2a import IR2A
from player.parser import *
import time
from pandas import DataFrame
from pandas import *
import numpy as np
from scipy import stats

class R2A_Panda(IR2A):


    def __init__(self, id):
        IR2A.__init__(self, id)
        self.average_type = "exponential_average"
                            #"exponential_average" #tipo de média dos filtros
                            #"sliding_window_average"
                            #"harmonic_mean"
        
        self.throughputs = []
        self.request_time = 0
        self.qi = []
        self.smooth = [] #average estimated and smooth band
        self.estimateband = [] #estimativa de banda
        
        self.k = 0.14
        self.w = 50000 #ganho constante de aproximadamente o valor minimo de segmentação do vídeo
        self.m = 10 #tamanho da minha janela
        
        self.beta = 0.15 #ganho do feedback de controle do buffer
        self.alfa = 0.1 
        self.e = 0.10 #ganho da zona neutra de quantização
        
        self.buffer = [] #lista para o buffer
        self.buffer_min = 40
        
        self.Tf = 1 #período de espera do próximo segmento
        
        self.t = 0
        self.deltaup = 0
        self.deltadown = 0

        self.quality = [0]

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        self.t = time.perf_counter() - self.request_time #calculo do período para a primeira requisição
        self.throughputs.append(msg.get_bit_length() / self.t) #medição da taxa da primeira requisição
        
        #calculo a estimativa da minha banda
        self.estimateband.append(self.Tf*self.k*(self.w - max(0,(0 - self.throughputs[-1] + self.w))) + 0)
        #troco o estimateband[0] igual a zero, então coloco o valor direto para não levar minha média
        #para baixo
        
        self.send_up(msg)#mando mensagem para cima
        
    def handle_segment_size_request(self, msg):

        self.request_time = time.perf_counter() #conto o meu tempo de requisição do último pacote
        
        if self.average_type is "exponential_average":
            #crio um dataframe para utilizar a função ewm de exponential weightedaverage
            df = DataFrame (self.estimateband,columns=['throughputs'])
            df.ewm(alpha=0.5).mean()
            valor = df.values.tolist()[-1][-1]
            
        if self.average_type is "harmonic_mean":
            valor = stats.hmean(self.estimateband)
            
        if self.average_type is "sliding_window_average":
            valor = np.mean(self.estimateband)
            
        
        #calculo o valor suavizado para o valor average da janela
        self.smooth.append(-self.Tf*self.alfa*( valor - self.estimateband[-1]) + valor)
        
        #CRIO UMA ZONA NEUTRA DE QUANTIZAÇÃO PARA QUE O ERRO DE QUANTIZAÇÃO NÃO SEJA SIGNIFICANTE
        self.deltaup = self.e * self.smooth[-1]
        qualityup = self.smooth[-1] - self.deltaup
        qualitydown = self.smooth[-1] - self.deltadown

        if self.quality[-1] < qualityup:
            self.quality.append(qualityup)
        elif qualityup <= self.quality[-1] and self.quality[-1] <= qualitydown:
            self.quality.append(self.quality[-1])
        else:
            self.quality.append(qualitydown)
        
        #QUANTIZO PARA MINHA LISTA DE QUALIDADES
        selected_qi = self.qi[0]
        for i in self.qi:
            if self.quality[-1] > i:
                selected_qi = i

        msg.add_quality_id(selected_qi)
        self.send_down(msg)
        
        #CRIO UM FEEDBACK PARA O TEMPO DO PRÓXIMO SEGMENTO
        
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
        self.estimateband.append(self.Tf*self.k*(self.w - max(0,(self.estimateband[-1] - self.throughputs[-1] + self.w))) + self.estimateband[-1])
        
        if len(self.estimateband) > self.m:
            del self.estimateband[0]
            del self.throughputs[0] #movendo minha janela excluído a primeira amostra 
       
        self.send_up(msg) #mando mensagem para cima

    def initialize(self):
        pass

    def finalization(self):
        pass