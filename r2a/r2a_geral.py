# -*- coding: utf-8 -*-
"""
Created on Sun Apr 18 14:24:07 2021

@author: Victor Hugo Marques
"""

# -*- coding: utf-8 -*-
"""
@author: Marcos F. Caetano (mfcaetano@unb.br) 03/11/2020

@description: PyDash Project

An implementation example of a FIXED R2A Algorithm.

the quality list is obtained with the parameter of handle_xml_response() method and the choice
is made inside of handle_segment_size_request(), before sending the message down.

In this algorithm the quality choice is always the same.
"""

from player.parser import *
from r2a.ir2a import IR2A
import time
import numpy as np
from copy import deepcopy
from scipy import stats


class R2A_geral(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = '' 
        self.qi = [] #lista com todas as qualidades de vídeo
        
        self.alfa = 0.2
        self.e = 0.15
        self.m = 10 #tamanho da janela observada
        self.w = 46980 #taxa de variação de acrescimo do bitrate como a menor taxa
            #do vídeo
        #to usando valores do vídeo
        self.k = 0.07#ganho do sistema
            #variando esse valor pra 0.14 tem um valor médio melhor, mas teve 6 pausas
        
        
        self.x_tio = [] #taxa transferência
        self.x_bar = [] #banda estimada
        self.y = [] #calculo da correnção segundo o PANDAs
        
        self.buffer = []
        
        self.lista_qual = [] #lista com as qualidades pedidas anteriormente
        
        self.request_time = 0 #calcular tempo de requerimento
        self.delta_tempo = 0 #variação do tempo da resposta
    

    def ExpAver(self, lista, alfa): #recebe uma lista e uma alfa para pesar
        i = 0
        num = 0 #meu resultado
        den = 0
        for i in range(len(lista),0,-1):
            num = num + pow(1-alfa, len(lista)-i+1)*lista[-(len(lista)-i+1)]
            den = den + pow(1-alfa, len(lista)-i+1)
        
        if den is 0:
            return False
        
        exp_avera = num/den
        
        return exp_avera    

    def handle_xml_request(self, msg):#passa pra baixo um pedido de conexão
        self.send_down(msg)
        
        self.request_time = time.time()

    
    def handle_xml_response(self, msg): #recebe o xml e análisa as qualidades de vívdeo possível      
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi() #tamanhos possíveis de vídeo análisados pelo parse
        
        self.delta_tempo = time.time() - self.request_time
        
        
        self.x_tio.append(msg.get_bit_length() / (self.delta_tempo) )
        
        #self.x_bar.append( self.delta_tempo*self.k*(self.w - max( 0 , 0 - self.x_tio[-1] + self.w)) + 0)
        self.x_bar.append( 1*self.k*(self.w - max( 0 , 0 - self.x_tio[-1] + self.w)) + 0)
        #substituição da fórmula pois self.x_bar[-1] neste momento é 0
        
        #escolho meu primeiro item para lista de qualidade de forma direta
        segment_estimate = self.x_tio[-1]
        selected_qi = self.qi[0]
        for i in self.qi:
            if segment_estimate > i:
                selected_qi = i         
        self.lista_qual.append(selected_qi)
        
        
        #atualizo também minha variável suavizada 
        self.y.append(0)
        
        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.time() #atualizando tempo de pedido
        
        for i in range(len(self.x_tio)):
            if self.x_tio[i] is 0:
                self.x_tio[i] = 1 #coloco um valor baixo só pra não quebrar o harmonic
                #testar em qual cenário aparecere zero, acho que somente em estado estacionário /????
        
        #CÁLCULO DO AVERAGE PELOS TRÊS JEITOS PROPOSTOS
        #SLIDING WINDOW
        #x_bar_smooth = np.mean(self.x_bar) #média da janela variante
        
        #HARMONIC MEAN
        #x_bar_smooth = stats.hmean(self.x_bar)
        
        #EXPOENTIAL
        x_bar_smooth = self.ExpAver(self.x_bar, self.alfa) #utilizando ao alfa que o Luiz falou que é bom
        
        #calculo de y corrigido Equação 9 artigo panda
        #self.y.append(-self.alfa*self.delta_tempo*(self.y[-1] - x_bar_smooth) + self.y[-1] )
        self.y.append(-self.alfa*(self.y[-1] - x_bar_smooth) + self.y[-1] )
        #CALCULO O Y PRA TER IDEIA DE SUA VARIAÇÃO
        
        #NÃO NECESSARIAMENTE PRECISAMOS DE UMA ZONA MORTA DE QUANTIZAÇÃO,
        #JÁ QUE NÃO FAZEMOS NENHUMA CORREÇÃO
        """deltaup = self.e * self.y[-1]
        deltadown = 0
            
        qualityup = self.y[-1] - deltaup
        qualitydown = self.y[-1]- deltadown

        if self.lista_qual[-1] < qualityup:
            self.lista_qual.append(qualityup)
        elif qualityup <= self.lista_qual[-1] and self.lista_qual[-1] <= qualitydown:
            self.lista_qual.append(self.lista_qual[-1])
        else:
            self.lista_qual.append(qualitydown)    """    
        
        segment_estimate = x_bar_smooth
        #EU OBSERVEI QUE O JEITO QUE ELE CALCULA O Y NÃO É ÚNICO. POSSO UTILIZAR 
        #O AVEREGE CALCULADO
       
        selected_qi = self.qi[0]
        for i in self.qi:
            if segment_estimate > i:
                selected_qi = i
        
        # time to define the segment quality choose to make the request
        msg.add_quality_id(selected_qi)
        self.send_down(msg)
    

    def handle_segment_size_response(self, msg):
        #atualizo meu tempo de resposta 
        self.delta_tempo = time.time() - self.request_time #variação de tempo para o último segmento
        
        self.x_tio.append(msg.get_bit_length() / self.delta_tempo)
        #self.x_bar.append( (self.delta_tempo*self.k*(self.w - max( 0 , (self.x_bar[-1] - self.x_tio[-1] + self.w)))) + self.x_bar[-1])
        self.x_bar.append( (1*self.k*(self.w - max( 0 , (self.x_bar[-1] - self.x_tio[-1] + self.w)))) + self.x_bar[-1])

        if len(self.x_bar) > self.m:
            del self.x_tio[0]
            del self.x_bar[0] #movendo minha janela excluído a primeira amostra 
        
        self.send_up(msg) #passo minha mensagem para cima 

    def initialize(self):
        pass

    def finalization(self):
        pass
    
    def exponential_average(lista, alfa): #recebe uma lista e uma alfa para pesar
        i = 0
        num = 0 #meu resultado
        den = 0
        for i in range(len(lista),0,-1):
            num = num + pow(1-alfa, len(lista)-i+1)*lista[-(len(lista)-i+1)]
            den = den + pow(1-alfa, len(lista)-i+1)
        
        if den is 0:
            return False
        
        exp_avera = num/den
        return exp_avera
