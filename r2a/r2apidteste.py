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


class R2APIDTeste(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = '' 
        self.qi = [] #lista com todas as qualidades de vídeo
        
        self.msg_size = 0 #variável local para tamanho da mensagem da vez
        self.segment_estimate = 0
        
        self.buffermax = 50
        self.buffermin = 20 #valores fixos para o esperado do buffer
        
        self.buffer_t = [0,0]
        self.buffer = [0,0] #lista com o histórioco do buffer
        self.erro_buffer = [0] #lista com os erros dos buffers para integração e derivação
        
        self.lista_taxa = [0] #lista com as qualidades pedidas anteriormente
        
        
        self.request_time = 0 #calcular tempo de requerimento
        self.delta_tempo = 0 #variação do tempo da resposta
        

    def handle_xml_request(self, msg):#passa pra baixo um pedido de conexão
        self.send_down(msg)
        
        self.request_time = time.time()

    def handle_xml_response(self, msg): #recebe o xml e análisa as qualidades de vívdeo possível      
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi() #tamanhos possíveis de vídeo análisados pelo parse
        
        self.delta_tempo = time.time() - self.request_time
        
        self.lista_taxa.append(msg.get_bit_length() / (self.delta_tempo) )
        
        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.time() #atualizando tempo de pedido
        
        self.segment_estimate = self.qi[10] #chute inicial de controle
        
        if len( list( self.whiteboard.get_playback_buffer_size()) ) > 5: #elimino as duas primeiras pra estabilizar respostas
            a = list( self.whiteboard.get_playback_buffer_size())
            #pego só o último pra atualizar a lista
            self.buffer.append(float(a[-1][1]))
            self.buffer_t.append(a[-1][0]) #pego o tempo das amostras e
            
            """
            print("tempo ------------->>>", self.buffer_t[-1])
        
            print("buffer ------------->>>", self.buffer[-1])
            """
            
            self.erro_buffer.append((self.buffermax - self.buffer[-1])/self.buffermax)
            
            ErroCon = self.erro_buffer[-1]
            ErroDer = (self.erro_buffer[-1]-self.erro_buffer[-2])/(self.erro_buffer[1]-self.erro_buffer[-2]+0.1)
            ErroInt =  (self.erro_buffer[-1]-self.erro_buffer[-2])*(self.erro_buffer[-1]+self.erro_buffer[-2])*0.5
            
            M = 0.7407*(0.6*ErroCon + 0.45*ErroInt + 0.30*ErroDer)
            
            #print("--------------------------->>>>>", M)
            """
            print("tipo ------------>>>", type(self.buffer[-1]))
            print("tipo ------------>>>", type(self.buffer_t[-1]))
            """
            #self.segment_estimate = self.segment_estimate*(1-M)
            self.segment_estimate = self.lista_taxa[-1]*(1-M)
            
        selected_qi = self.qi[0]
        for i in self.qi:
            if self.segment_estimate > i:
                selected_qi = i
        
        # time to define the segment quality choose to make the request
        msg.add_quality_id(selected_qi)
        self.send_down(msg)
    

    def handle_segment_size_response(self, msg):
        #atualizo meu tempo de resposta 
        self.delta_tempo = time.time() - self.request_time #variação de tempo para o último segmento
        
        self.lista_taxa.append(msg.get_bit_length() / (self.delta_tempo) ) #calculo a velocidade da vez
        
        self.send_up(msg) #passo minha mensagem para cima 

    def initialize(self):
        pass

    def finalization(self):
        pass
