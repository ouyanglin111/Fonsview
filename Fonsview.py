#!/usr/bin/env python
# coding=utf8

from socket import *
import time
import re
import sys
from random import Random


# some setting
connect_info = {
    "HOST": "",
    "PORT": 8500,
    "BUFSIZE": 8192,
    "CMS_IP": "172.16.199.240",
    "CMS_PORT": 6600,
    "TCGSURL": "/cms/rest/tcgs/reply",
    "TVGWURL": "/cms/rest/tvgw/reply",
    "CSPURL": "/recieveC2Standard",
    "URL": ""
}


# 生成随机字符串函数
def random_str(randomlength):
    str = ''
    # chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    BeChosenChars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    #字符串右边界索引值
    length = len(BeChosenChars) - 1
    # 将Random函数命名为random
    random = Random()
    # 根据传入的要生成的串长度，随机生成由小写字母及数字组成的字符串
    for i in range(randomlength):
        str += BeChosenChars[random.randint(0, length)]
    return str


# 避免数据分段传输，设置超时函数，接收所有数据
def genmsg_recv(the_socket, timeout = 2):
    # make socket non blocking
    the_socket.setblocking(0)
    # total data partwise in an array
    total_data = []
    data = ''
    # beginning time
    begin = time.time()
    while 1:
        # if you got some data, then break after timeout
        if total_data and time.time() - begin > timeout:
            break
        # if you got no data at all, wait a little longer, twice the timeout
        elif time.time() - begin > timeout*2:
            break
    # recv something
    try:
        data = the_socket.recv(8192)
        if data:
            total_data.append(data)
            # change the beginning time for measurement
            begin = time.time()
        else:
            # sleep for sometime to indicate a gap
            time.sleep(0.1)
    except:
        pass
    # join all parts to make final string
    return ''.join(total_data)


# 构造200 OK消息
def genmsg_response(bodytype):
    http_body = ''
    contenttype = ''
    if bodytype == 1:
        http_body = '{"ResultCode":0}'
        contenttype = 'application/json'
    if bodytype == 2:
        http_body = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>' \
               '<ns2:ResultNotifyResponse xmlns:ns2="iptv"><CSPResult><errorDescription>success</errorDescription>' \
               '<result>0</result></CSPResult></ns2:ResultNotifyResponse></soap:Body></soap:Envelope>'
        contenttype = 'text/xml; charset=utf-8'

    contentlength = str(len(http_body))
    msg_res = 'HTTP/1.1 200 OK\r\n'
    msg_res += 'Content-Length: ' + contentlength + '\r\n'
    msg_res += 'Content-Type: ' + contenttype + '\r\n'
    msg_res += 'Server: lighttpd/1.4.28\r\n'
    msg_res += '\r\n'
    msg_res += http_body + '\r\n'
    return msg_res


# 构造post消息
def genmsg_post(url, host, port, val1, val2, bodynum):

    contentlength = ''
    contenttype = ''
    http_body = ''
    if bodynum == 2:
        http_body = '<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:soapenv=' \
               '"http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ' \
               'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><ExecCmd xmlns="iptv">' \
               '<CSPID xmlns="">fonsview</CSPID><LSPID xmlns="">00000000</LSPID>' \
               '<CorrelateID xmlns="">%s</CorrelateID>' \
               '<CmdFileURL xmlns="">ftp://ftpuser:ftpuser@172.16.199.242/adi/%s.xml</CmdFileURL></ExecCmd>' \
               '</soapenv:Body></soapenv:Envelope>' % (val1, val2)
        contenttype = 'text/xml; charset=utf-8'

    elif bodynum == 3:
        http_body = '<?xml version="1.0" encoding="utf-8"?><task_ack><id>%s</id><errcode>%s</errcode>' \
               '<errmsg>tcgs return result</errmsg>' \
               '<dir>ftp://anonymous:anonymous@172.16.200.250/Media/2Guns/2/2.m3u8</dir></task_ack>' % (val1, val2)
        contenttype = 'text/xml; charset=utf-8'

    elif bodynum == 4:
        http_body = '{"MsgType":"MovieAddCmpl ","RequestId":%s,"ContentId":"%s","ProviderId":"mango","Download' \
                    'URL":"ftp://ftpuser:ftpuser@222.68.210.101:21/vbr_7.5m_high_4.0.ts","ResultCode":0}' % (val1, val2)
        contenttype = 'application/json'

    else:
        print "No match"
    contentlength = str(len(http_body))
    reply_result = "POST " + url + " HTTP/1.0\r\n"
    reply_result += "Host: " + host + ":" + str(port) + "\r\n"
    reply_result += "User-Agent: Fonsview/SIT\r\n"
    reply_result += "Content-Type: " + contenttype + "\r\n"
    reply_result += "Content-Length: " + contentlength + "\r\n"
    reply_result += "\r\n"
    reply_result += http_body + "\r\n"
    print '---------------------------->'
    print reply_result
    return reply_result


# 定义查找TaskID的函数
def findtask(pending_data):
    # 对数据进行分割处理，以\r\n作为分割点，生成列表
    split_data = pending_data.split('\r\n')
    # 对xml消息进行处理，去除换行符\n
    ldata = split_data[len(split_data)-1].strip('\n')
    # print '\033[1;32;55m收到请求XML:%s\033[0m\n',List_Data
    # 正则表达式：找出<id></id>间的数据
    regular_data = re.findall(r'<id>(.*?)</id>', ldata)
    # 得出TaskID的字符串
    taskid = regular_data[0]
    return taskid


# 定义查找contentId和requestId的函数
def findcid(dealing_data):
    split_data = dealing_data.split('\r\n')
    ldata = split_data[len(split_data)-1].strip('\n')
    regular_data_cid = re.findall(r'"ContentId":"(.*?)",', ldata)
    #also you can use:re.match(r'.*"ContentId":"(.*?)",.*', str).group(1)
    regular_data_reqid = re.findall(r'"RequestId":(.*?),', ldata)
    cid = regular_data_cid[0]
    reqid = regular_data_reqid[0]
    return cid, reqid

# 定义监听Sock请求的函数
def listensock(val):
    # 监听链接
    frcms_sock, addr = sersock.accept()
    req_data = genmsg_recv(frcms_sock)
    print '<----------------------------'
    print req_data
    print '---------------------------->'
    print genmsg_response(val)
    frcms_sock.send(genmsg_response(val))
    time.sleep(2)
    frcms_sock.close()
    return req_data


# 定义主动请求Sock的函数
def connsock(val1, val2, val3):
    # 建立请求CMS的Socket通道，并链接
    tocms_sock = socket(AF_INET, SOCK_STREAM)
    tocms_sock.connect((connect_info["CMS_IP"], connect_info["CMS_PORT"]))
    # 发送请求数据
    tocms_sock.send(genmsg_post(connect_info["URL"], connect_info["CMS_IP"], connect_info["CMS_PORT"], val1, val2, val3))
    # 接收返回响应数据
    print '<----------------------------'
    print tocms_sock.recv(connect_info["BUFSIZE"])
    time.sleep(10)
    tocms_sock.close()


# 主函数
def main(order):
    #待开发的C1接口
    if order == 1:
        print "Developing..."

    # 如果传入1时，判断为C2的接口测试
    if order == 2:
        # 设置dict中的URL值为CSPURL的值
        connect_info["URL"] = connect_info["CSPURL"]
        # 设置dict中的CMS的端口为6070
        connect_info["CMS_PORT"] = 6070
        # 传入xml文件名，只需要文件名，无需后缀
        xmlfile = raw_input("Insert Xml Name:")
        # 产生32位长度的correlateid
        correlateid = random_str(32)
        # 调用connsock函数，传入变量correlateid,xmlfile,及genmsg_post函数中需要的bodynum值
        connsock(correlateid, xmlfile, 2)
        time.sleep(2)
        # 调用listensock函数，传入值2，代表genmsg_response函数需要的bodytype，以判断200OK回复的类型为xml
        listensock(2)

    # 如果传入3时，判断为TCGS的接口测试
    if order == 3:
        # 设置dict中的URL值为TCGSURL的值
        connect_info["URL"] = connect_info["TCGSURL"]
        # 设置dict中的CMS的端口为6600
        connect_info["CMS_PORT"] = 6600
        # 传入转码结果errorcode
        errorcode = raw_input("Errorcode:")
        print 'Wait from request message!!!'
        # 调用listensock函数，传入值1，代表genmsg_response函数需要的bodytype，以判断200OK回复的类型为json
        recvdata = listensock(1)
        time.sleep(15)
        # 调用findtask函数，返回TaskId
        tid = findtask(recvdata)
        # 调用connsock函数，传入变量tid,errorcode,及genmsg_post函数中需要的bodynum值
        connsock(tid, errorcode, 3)

    # 如果传入4时，判断为TVGW的接口测试
    if order == 4:
        # 设置dict中的URL值为TVGWURL的值
        connect_info["URL"] = connect_info["TVGWURL"]
        # 设置dict中的CMS的端口为6600
        connect_info["CMS_PORT"] = 6600
        print 'Wait from request message!!!'
        # 调用listensock函数，传入值1，代表genmsg_response函数需要的bodytype，以判断200OK回复的类型为json
        recvdata2 = listensock(1)
        time.sleep(5)
        # 调用findcid函数，返回contentid,requestid
        contentid, requestid = findcid(recvdata2)
        # 调用connsock函数，传入变量,requestid,contentid及genmsg_post函数中需要的bodynum值
        connsock(requestid, contentid, 4)



# 定义menu函数，作为脚本显示入口
def show_menu():
    menu_list = """
*********************
1 C1 Interface
2 C2 Interface
3 TCGS Interface
4 TVGW Interface
5 Quit
*********************
Choose it:"""
    global sersock
    way = raw_input("[O]One Times or [A]All times:").strip()[0].lower()
    if way in 'oa':
        if way == 'a':
            try:
                sersock = socket(AF_INET, SOCK_STREAM)
                sersock.bind((connect_info["HOST"], connect_info["PORT"]))
                sersock.listen(5)
                choice2 =raw_input(menu_list).strip()[0]
                if choice2 not in '1234':
                    sys.exit()
                else:
                    while True:
                        # 创建Socket通道，以8080为本地端口
                        main(int(choice2))
            except (UnboundLocalError, IndexError, EOFError, KeyboardInterrupt):
                sersock.close()
        else:
            sersock = socket(AF_INET, SOCK_STREAM)
            sersock.bind((connect_info["HOST"], connect_info["PORT"]))
            sersock.listen(5)
            val = 0
            while not val:
                try:
                    choice = raw_input(menu_list)
                    if choice.isdigit() and int(choice) in [1, 2, 3, 4, 5]:
                        if choice in "1234":
                            main(int(choice))
                        else:
                            print "\033[1;34;55mBye Bye!\033[0m"
                            sersock.close()
                            val = 1
                    else:
                        print "Invalid Choice,be sure it,choose again!"
                except (UnboundLocalError, IndexError, EOFError, KeyboardInterrupt):
                        print "Error Occur!"
    else:
        print 'Bad choice,exit!!!'
        sys.exit()

# 主函数
if __name__ == '__main__':
    show_menu()

