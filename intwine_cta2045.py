# BSD 3-Clause License
# Copyright (c) 2018, Intwine Connect, LLC.

# For a full description of the Intwine CTA-2045 Wifi UCMs, see:
# https://github.com/IntwineConnect/cta2045-wifi-modules

import urllib2
import json
import socket
from httplib import BadStatusLine


class IntwineCtaUcm:
    UCMip = '192.168.0.3'
    UCMname = 'Intwine UCM'
    UCMtype = None
    current_sgd_state = 0
    sgd_info = None

    HTTPmethods = {'shed': 'POST',
                   'normal': 'POST',
                   'grid_emergency': 'POST',
                   'critical_peak': 'POST',
                   'cur_price': 'POST',
                   'next_price': 'POST',
                   'change_level': 'POST',
                   'time_remaining': 'POST',
                   'time_sync': 'POST',
                   'state_sgd': 'GET',
                   'info_sgd': 'GET',
                   'load_up': 'POST',
                   'start_cycling': 'POST',
                   'stop_cycling': 'POST',
                   'comm_state': 'POST',
                   'commodity': 'GET',
                   'set_setpoint': 'POST',
                   'get_setpoint': 'GET',
                   'get_temperature': 'GET'
                   }

    URLmap = {'shed': '/load.cgi?',
              'normal': '/load.cgi?',
              'grid_emergency': '/load.cgi?',
              'critical_peak': '/load.cgi?',
              'cur_price': '/price.cgi?',
              'next_price': '/price.cgi?',
              'change_level': '/load.cgi?',
              'time_remaining': '/price.cgi?',
              'time_sync': '/time.cgi?',
              'state_sgd': '/state_sgd.cgi?',
              'info_sgd': '/info_sgd.cgi',
              'load_up': '/load.cgi?',
              'start_cycling': '/load.cgi?',
              'stop_cycling': '/load.cgi?',
              'comm_state': '/comm.cgi?',
              'commodity': '/commodity.cgi',
              'set_setpoint' : '/setpoint.cgi',
              'get_setpoint' : '/setpoint.cgi',
              'get_temperature' : '/temperature.cgi'
              }

    device_type = {
        0 : "Unspecified Type",
        1 : "Water Heater - Gas",
        2 : "Water Heater - Electric",
        3 : "Water Heater - Heat Pump",
        4 : "Central AC - Heat Pump",
        5 : "Central AC - Fossil Fuel Heat",
        6 : "Central AC - Resistance Heat",
        7 : "Central AC (only)",
        8 : "Evaporative Cooler",
        9 : "Baseboard Electric Heat",
        10 : "Window AC",
        11 : "Portable Electric Heater",
        12 : "Clothes Washer",
        13 : "Clothes Dryer - Gas",
        14 : "Clothes Dryer - Electric",
        15 : "Refrigerator/Freezer",
        16 : "Freezer",
        17 : "Dishwasher",
        18 : "Microwave Oven",
        19 : "Oven - Electric",
        20 : "Oven - Gas",
        21 : "Cook Top - Electric",
        22 : "Cook Top - Gas",
        23 : "Stove - Electric",
        24 : "Stove - Gas",
        25 : "Dehumidifier",
        32 : "Fan",
        48 : "Pool Pump - Single Speed",
        49 : "Pool Pump - Variable Speed",
        50 : "Electric Hot Tub",
        64 : "Irrigation Pump",
        4096 : "Electric Vehicle",
        4097 : "Hybrid Vehicle",
        4352 : "Electric Vehicle Supply Equipment - general (SAE J1772)",
        4353 : "Electric Vehicle Supply Equipment - Level 1 (SAE J1772)",
        4354 : "Electric Vehicle Supply Equipment - Level 2 (SAE J1772)",
        4355 : "Electric Vehicle Supply Equipment - Level 3 (SAE J1772)",
        8192 : "In Premises Display",
        20480 : "Energy Manager",
        24576 : "Gateway Device"
        }

    sgd_state_map = {0: "Idle Normal",
                     1: "Running Normal",
                     2: "Running Curtailed",
                     3: "Running Heightened",
                     4: "Idle Curtailed",
                     5: "SGD Error Condition",
                     6: "Idle Heightened",
                     7: "Cycling On",
                     8: "Cycling Off",
                     9: "Variable Following",
                     10: "Variable Not Following",
                     11: "Idle, Opted Out",
                     12: "Running, Opted Out"
                     }

    def is_rsp_good(self, rsp):
        if rsp.get('http_code', None) == '200':
            return True
        else:
            return rsp

    def forward_UCM(self, mesdict):
        """
        parses message and issues REST API CTA command
        """
        # deserialize message string
        # TODO long method with too many functionalities. Refactor
        messageSubject = mesdict.get('message_subject', None)

        # ignore anything posted to the topic other than notifications of new events
        if messageSubject != 'new_event':
            return json.dumps({'status': 'Not a new event message'})

        eventName = mesdict.get('event_name', 'normal')
        #print('***NEW EVENT*** of type <{event}> for  UCM <{name}>'.format(event=eventName, name=self.UCMname))

        # get URL for http://' + self.UCMip + page
        page = self.URLmap.get(eventName, '/load.cgi?')
        requestURL = 'http://' + self.UCMip + page
        UCMrequest = urllib2.Request(requestURL)
        # determine whether to use GET, POST, or anything else if necessary
        method = self.HTTPmethods.get(eventName, 'POST')

        if method == 'POST':
            # remove key-value pairs that aren't needed for the REST API message
            mesdict.pop('message_subject', None)
            mesdict.pop('priority', None)

            cleanmessage = json.dumps(mesdict)
            UCMrequest.add_data(cleanmessage)

        #print('sending ' + method + ' for page ' + requestURL + ' for ' + eventName)

        # send REST API CTA command
        try:
            result = urllib2.urlopen(UCMrequest, timeout=10)
        except urllib2.URLError, e:
            #print('an urllib2 error of type {error} occurred while sending message to {ucm}'.format(error=e, ucm=self.UCMname))
            notification = {"message_subject": "urllib2_failure"}
            return json.dumps(notification)
        except socket.timeout, e:
            # Sometimes times out once, but should work on the second time.
            # TODO ugly approach. refactor or get bug fixed
            try:
                result = urllib2.urlopen(UCMrequest, timeout=10)
            except urllib2.URLError, e:
                #print('an urllib2 error of type {error} occurred while sending message to {ucm}'.format(error=e, ucm=self.UCMname))
                return {"message_subject": "urllib2_failure"}
            except socket.timeout, e:
                return {"message_subject": "timeout"}
            except BadStatusLine:
                #print('ERROR: Bad status line')
                return {"message_subject": "Bad status line"}
        except BadStatusLine:
            #print('ERROR: Bad status line')
            return {"message_subject": "Bad status line"}

        HTTPcode = result.getcode()
        UCMresponse = result.read()
        if len(UCMresponse) > 0 and method == 'GET':
            UCMresponsedict = json.loads(UCMresponse)
        else:
            UCMresponsedict = {}
        UCMresponsedict['message_subject'] = 'UCMresponse'
        UCMresponsedict['http_code'] = str(HTTPcode)

        # publish notification of response receipt with REST API response fields if applicable
        #print('###RECEIVED A RESPONSE### relative to event #from <{name}> with HTTP code <{code}> ''and body message : {body}'.format(name=self.UCMname, code=HTTPcode, body=UCMresponse))

        return UCMresponsedict

############################################################
## Simple DR                                              ##
############################################################

    def send_comm_good(self):
        message = {'message_subject': 'new_event',
                   'event_name': 'comm_state',
                   'commstate': 'good'}
        return self.is_rsp_good(self.forward_UCM(message))

    def run_normal(self):
        message = {'message_subject': 'new_event',
                   'event_name' : 'normal'}
        return self.is_rsp_good(self.forward_UCM(message))

    def shed(self, duration):
        message = {'message_subject': 'new_event',
                   'event_name' : 'shed',
                   'event_duration': str(duration)}
        return self.is_rsp_good(self.forward_UCM(message))

    def critical_peak(self, duration):
        message = {'message_subject': 'new_event',
                   'event_name' : 'critical_peak',
                   'event_duration': str(duration)}
        return self.is_rsp_good(self.forward_UCM(message))

    def grid_emergency(self, duration):
        message = {'message_subject': 'new_event',
                   'event_name' : 'grid_emergency',
                   'event_duration': str(duration)}
        return self.is_rsp_good(self.forward_UCM(message))

    def load_up(self, duration):
        message = {'message_subject': 'new_event',
                   'event_name' : 'load_up',
                   'event_duration': str(duration)}
        return self.is_rsp_good(self.forward_UCM(message))

############################################################
## Intermediate DR                                        ##
############################################################

    def load_percent(self, percent):
        # negative value => power is produced by the SGD
        # positive value => power is consumed by the SGD
        message = {'message_subject': 'new_event',
                   'event_name' : 'change_level',
                   'load_percent': str(percent)}
        return self.is_rsp_good(self.forward_UCM(message))

    # Present Relative Prive

    # Next Period Relative Price

    # Time remainging in current Price Period

    def check_sgd_state(self):
        message = {'message_subject': 'new_event',
                   'event_name' : 'state_sgd'}
        ucm_response = self.forward_UCM(message)
        if "code" in ucm_response:
            code = int(ucm_response.get("code"))
            self.current_sgd_state = code
            return {'code': code, 'meaning': self.sgd_state_map.get(code, "Unknown")}
        else:
            return {'message_subject': 'code not found'}

    def get_sgd_info(self):
        message = {'message_subject': 'new_event',
                   'event_name' : 'info_sgd' }
        return self.forward_UCM(message)

    def get_setpoint(self):
        message = {'message_subject': 'new_event',
                   'event_name' : 'get_setpoint' }
        return self.forward_UCM(message)

    def set_setpoint(self, units, value1=None, value2=None):
        unit_map = {'F': '0',
                    'C': '1'}
        message = {'message_subject': 'new_event',
                   'event_name' : 'set_setpoint',
                   'device_type': str(self.UCMtype),
                   'units': unit_map.get(units,'')}
        if value1:
            message['setpoint1'] = str(value1)
        if value2:
            message['setpoint2'] = str(value2)

        return self.is_rsp_good(self.forward_UCM(message))

    def get_temperature(self):
        message = {'message_subject': 'new_event',
                   'event_name' : 'get_temperature' }
        return self.forward_UCM(message)

    def get_commodity(self):
        message = {'message_subject': 'new_event',
                   'event_name' : 'commodity'}
        return self.forward_UCM(message)

    def send_ucm_command(self, msg_dict):
        return self.forward_UCM(msg_dict)

    def __init__(self, ip, name):
        self.UCMip = ip
        self.UCMname = name

        if not self.sgd_info:
            info = self.get_sgd_info()
            if info.get('http_code',None) == '200':
                self.sgd_info = info
                self.device_type = info.get('Device Type', 0)
