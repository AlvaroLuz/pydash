# -*- coding: utf-8 -*-
"""
@author: Álvaro Veloso Cavalcanti Luz (180115391@aluno.unb.br) 28/11/2020

@description: PyDash Project

An implementation of a FDASH ABR algorithm in a R2A Algorithm.

the quality list is obtained with the parameter of handle_xml_response() method and the choice
is made inside of handle_segment_size_request(), before sending the message down.

In this algorithm the quality choice is always the same.
"""

from player.parser import *
from r2a.ir2a import IR2A
import time
import math

class R2AFDash(IR2A):
    
    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.qi_index = 9
        self.time_last_buffer_check = 0
        self.now_diff_buffer_time = 0
        self.first_package = True
        self.buffer_time = 0
        self.timestamp_last_buffer_add =0
        self.before_diff_buffer_time = -1
        self.request_time = 0
        self.ri = []

    def handle_xml_request(self, msg):
        # getting the initial time of the request for calculating the throughput
        self.request_time  = time.perf_counter()

        self.send_down(msg)

    def handle_xml_response(self, msg):
        # getting qi list
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()
        
        # getting the response time for calculating the throughput
        request_processing_time = time.perf_counter() - self.request_time
        bit_size = msg.get_bit_length()
        self.ri.append(bit_size/(request_processing_time))

        self.send_up(msg)

    def handle_segment_size_request(self, msg):

        # time to define the segment quality choose to make the request
        #variable to the first passage
        #can be improved
        if(self.first_package == False):
            buffer_playback = self.whiteboard.get_playback_buffer_size()
            i = 0   
            for playback in buffer_playback:
                if (playback[0] > self.timestamp_last_buffer_add):
                    if ((playback[1]> buffer_playback[i-1][1])or(len(buffer_playback) == 1)):
                        self.now_diff_buffer_time = playback[1] - self.time_last_buffer_check
                        self.time_last_buffer_check = playback[1] - 1
                        self.timestamp_last_buffer_add = playback[0]
                i = i + 1
            
            #verbal variables for referring to the buffer size
            Close, Long, Short = False, False, False
            if(self.time_last_buffer_check<10):
                Short = True 
            elif(self.time_last_buffer_check>=20):
                Long = True
            else:
                Close = True

            delta_diff_buffer_time = self.now_diff_buffer_time - self.before_diff_buffer_time

            #verbal variables for referring to the buffer variations in size
            Rising, Falling, Steady = False, False, False 
            if (delta_diff_buffer_time>0):
                Rising = True
            elif(delta_diff_buffer_time<0):
                Falling = True
            else:
                Steady = True
            
            #choosing the non null minimum value
            if ((delta_diff_buffer_time<self.time_last_buffer_check)):
                if(delta_diff_buffer_time == 0):
                    r = self.time_last_buffer_check
                else:
                    r = delta_diff_buffer_time
            else:
                if (self.time_last_buffer_check == 0):
                    r = delta_diff_buffer_time
                else:
                    r = self.time_last_buffer_check
            
            #evaluating the controllers and rules
            r1,r2,r3,r4,r5,r6,r7,r8,r9 = 0,0,0,0,0,0,0,0,0
            print(f'Controladores: {self.time_last_buffer_check},{delta_diff_buffer_time}')
            if Short   and Falling:
                r1 = r
            elif Close and Falling:
                r2 = r
            elif Long  and Falling:
                r3 = r
            elif Short and Steady:
                r4 = r
            elif Close and Steady:
                r5 = r
            elif Long  and Steady:
                r6 = r
            elif Short and Rising:
                r7 = r
            elif Close and Rising:
                r8 = r
            else:
                r9 = r
    
            print(f"{r1},{r2},{r3},{r4},{r5},{r6},{r7},{r8},{r9}")

            I  = math.sqrt((r9**2))
            SI = math.sqrt((r6**2)+(r8**2))
            NC = math.sqrt((r3**2)+(r5**2)+(r7**2))
            SR = math.sqrt((r2**2)+(r4**2))
            R  = math.sqrt((r1**2))    

            #possible improvement
            #defining the fuzzy controller constants
            arg_dict = {"N2": 0.25,
                        "N1": 0.5 ,
                        "Z" : 1   ,
                        "P1": 1.5 ,
                        "P2": 2.0   
                    }
            
            #calculating fuzzy controller
            f = (arg_dict["N2"] * R) + (arg_dict["N1"] * SR) + (arg_dict["Z"] * NC) + (arg_dict["P1"] * SI) + (arg_dict["P2"]* I) 
            f = f/(R+SR+NC+SI+I)
            
            rd = 0 
            #calculating mean throughput rate 
            for throughput in self.ri:
                rd = rd+(throughput/len(self.ri))
            
            #defining next segment bit size
            bi = f * rd

            self.qi_index = 0
            for quality in self.qi:
                if (self.qi_index == 19):
                    break
                elif(quality < bi):
                    self.qi_index= self.qi_index+1
            
            print(f'Exibindo o valor de Bi+1 = {bi}, f = {f}, rd = {rd}')
        
        msg.add_quality_id(self.qi[self.qi_index])
        #variable to the first passage
        #possible improvement
        self.first_package = False        
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        #getting the bit size of the message to calculate throughput
        #is it necessary to be here
        buffer_playback = self.whiteboard.get_playback_buffer_size()
        i = 0
        for playback in buffer_playback:
            if (playback[0] > self.timestamp_last_buffer_add):
                if ((playback[1]> buffer_playback[i-1][1])or(len(buffer_playback) == 1)):
                    self.before_diff_buffer_time = self.now_diff_buffer_time
            i = i + 1

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
