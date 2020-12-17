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
from statistics import mean
class R2AFDash(IR2A):
    
    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.qi_index = 0
        self.now_buffer_size = 0
        self.before_buffer_size = 0
        self.first_package = True
        self.buffer_time = 0
        self.ri = []
        self.request_time = 0
        self.previous_quality_index = 0
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

        #calculating and storing the throughput of the previous segment
        self.ri.append(bit_size/(request_processing_time))

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # timer used to calculate the throughput
        self.request_time  = time.perf_counter()
        #variable to the first passage
        if(self.first_package == False):
            #obtaining the current buffer size
            buffer_playback = self.whiteboard.get_playback_buffer_size()
            
            self.before_buffer_size = self.now_buffer_size
            self.now_buffer_size = buffer_playback[-1][1] - 1

            #verbal variables for referring to the buffer size
            Close, Long, Short = False, False, False
            if(self.now_buffer_size<35):
                Short = True 
            elif(self.now_buffer_size>=50):
                Long = True
            else:
                Close = True

            delta_buffer_size = self.now_buffer_size - self.before_buffer_size

            #verbal variables for referring to the buffer variations in size
            Rising, Falling, Steady = False, False, False 
            if (delta_buffer_size>0):
                Rising = True
            elif(delta_buffer_size<0):
                Falling = True
            else:
                Steady = True
            
            #evaluating the controllers and rules
            r1,r2,r3,r4,r5,r6,r7,r8,r9 = 0,0,0,0,0,0,0,0,0
            r = 1
            print(f"Conditional controlers: {self.now_buffer_size},{delta_buffer_size}")
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
    
            #obtaining the fuzzy controller variables 
            I  = math.sqrt((r9**2))
            SI = math.sqrt((r6**2)+(r8**2))
            NC = math.sqrt((r3**2)+(r5**2)+(r7**2))
            SR = math.sqrt((r2**2)+(r4**2))
            R  = math.sqrt((r1**2))    

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
            
            #calculating mean throughput rate 
            rd = mean(self.ri)/3

            #defining next segment bit size
            bi = f * rd

            #obtaining the quality index for the next segment
            self.qi_index = 0
            for quality in self.qi:
                if (self.qi_index == 19):
                    break
                elif(quality < bi):
                    self.qi_index= self.qi_index+1
            
            print(f'Showing the obtained values for: Bi+1 = {bi}; f = {f}; rd = {rd}.')
            
            #conditionals used for avoiding unecessary oscilations in quality
            self.predict_buffer_new_index = self.now_buffer_size + (((self.ri[-1]/3)/self.qi[self.qi_index])*60) 
            self.predict_buffer_previous_index = self.now_buffer_size + (((self.ri[-1]/3)/self.qi[self.previous_quality_index])*60)
            
            if ((self.qi[self.qi_index]>self.qi[self.previous_quality_index])and(self.predict_buffer_new_index<35)):
                self.qi_index = self.previous_quality_index
            elif ((self.qi[self.qi_index]<self.qi[self.previous_quality_index])and(self.predict_buffer_previous_index>35)):
                self.qi_index = self.previous_quality_index
            
            self.previous_quality_index = self.qi_index
            
        #negating the boolean that represents the first passage
        self.first_package = False

        #forwarding the message
        msg.add_quality_id(self.qi[self.qi_index])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        #getting the bit size of the message to calculate throughput
        request_processing_time = time.perf_counter() - self.request_time
        bit_size = msg.get_bit_length()

        #calculating and storing the throughput of the previous segment
        self.ri.append(bit_size/(request_processing_time))

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
