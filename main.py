'''
这个位置要根据自己python开发环境的安装进行更改

'''
#! C:\Users\Administrator\AppData\Local\Programs\Python\Python35-32\python.exe
#coding: utf-8
''' 更改记录
'''
import os
import sys
import json
import time
import threading

from bottle import route, run, redirect
from bottle import static_file, template

from serial import Serial
from serial.tools.list_ports import comports

from websocket_server import WebsocketServer


@route('/')
def index(info=''):
    return template('index.html', sers=[(desc, port) for port, desc, hwid in comports()])

@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='./static/')


class SerialServer(object):
    ''' 串口硬件  ==>  串口服务器（ws server）  ==>  电脑浏览器（ws client）
        电脑浏览器（ws client） ==>  串口服务器（ws server）  ==>  串口硬件
    '''
    def __init__(self, websocket_server_port):
        super(SerialServer, self).__init__()

        self.ser = Serial()

        self.ws_client = None

        self.ws = WebsocketServer(port=websocket_server_port)
        self.ws.set_fn_new_client(lambda client, server: self.ws_new_client(client))
        self.ws.set_fn_message_received(lambda client, server, message: self.ws_message_received(message))

        threading.Thread(target=self.ws.run_forever).start()

        threading.Thread(target=self.ser_receive).start()

    def ws_new_client(self, client):
        self.ws_client = client

    def ws_message_received(self, message):
        msg = json.loads(message)
        if 'cmd' in msg:
            if msg['cmd'] == 'open serial':
                print(msg['port'])
                print(msg['baud'])

                if not self.ser.is_open:
                    try:
                        self.ser.port     = msg['port']
                        self.ser.baudrate = msg['baud']
                        self.ser.open()
                    except Exception as e:
                        print(e)
                        self.ws.send_message(self.ws_client, json.dumps({'cmd': 'serial closed'}))
                    else:
                        self.ws.send_message(self.ws_client, json.dumps({'cmd': 'serial opened'}))

            elif msg['cmd'] == 'close serial':
                print('close')

                if self.ser.is_open:
                    self.ser.close()

                    self.ws.send_message(self.ws_client, json.dumps({'cmd': 'serial closed'}))

        elif 'data' in msg:
            print(msg['data'])
            if self.ser.is_open:
                self.ser.write(msg['data'].encode())        

    def ser_receive(self):
        while True:
            if self.ser.is_open:
                num = self.ser.in_waiting
                if num > 0:
                    bytes = self.ser.read(num)
                    print(bytes)

                    if self.ws_client:
                        self.ws.send_message(self.ws_client, json.dumps({'data': bytes.decode()}))

            time.sleep(0.1)


if __name__ == '__main__':
    ser = SerialServer(websocket_server_port=9978)
    #实现网络上ip地址访问，这个地方需要用ip地址的方式
    run(host='192.168.1.14', port='8080', debug=True, reloader=True) 
