from bilibili import bilibili
from statistics import Statistics
from printer import Printer
import utils
import asyncio
import random
import struct
import json
import re
import requests
import sys



class bilibiliClient():

    def __init__(self):
        self.bilibili = bilibili()
        self._reader = None
        self._writer = None
        self._uid = None
        self.connected = False
        self._UserCount = 0


        self.dic_bulletin = {
            'cmd': 'str',
            'msg': 'str',
            'rep': 'int',
            'url': 'str'
        }

    async def connectServer(self):
        try:
            reader, writer = await asyncio.open_connection(self.bilibili.dic_bilibili['_ChatHost'], self.bilibili.dic_bilibili['_ChatPort'])
        except:
            print("# 连接无法建立，请检查本地网络状况")
            return
        self._reader = reader
        self._writer = writer
        if (await self.SendJoinChannel(self.bilibili.dic_bilibili['roomid']) == True):
            self.connected = True
            Printer().printlist_append(['join_lottery', '', 'user', '连接弹幕服务器成功'], True)
            await self.ReceiveMessageLoop()

    async def HeartbeatLoop(self):
        while self.connected == False:
            await asyncio.sleep(0.5)

        Printer().printlist_append(['join_lottery', '', 'user', '弹幕模块开始心跳'], True)

        while self.connected == True:
            await self.SendSocketData(0, 16, self.bilibili.dic_bilibili['_protocolversion'], 2, 1, "")
            await asyncio.sleep(30)

    async def SendJoinChannel(self, channelId):
        self._uid = (int)(100000000000000.0 + 200000000000000.0 * random.random())
        body = '{"roomid":%s,"uid":%s}' % (channelId, self._uid)
        await self.SendSocketData(0, 16, self.bilibili.dic_bilibili['_protocolversion'], 7, 1, body)
        return True

    async def SendSocketData(self, packetlength, magic, ver, action, param, body):
        bytearr = body.encode('utf-8')
        if packetlength == 0:
            packetlength = len(bytearr) + 16
        sendbytes = struct.pack('!IHHII', packetlength, magic, ver, action, param)
        if len(bytearr) != 0:
            sendbytes = sendbytes + bytearr
        # print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), sendbytes)
        try:
            self._writer.write(sendbytes)
        except:
            print(sys.exc_info()[0], sys.exc_info()[1])
            self.connected = False

        await self._writer.drain()

    async def ReadSocketData(self, len_wanted):
        bytes_data = b''
        if len_wanted == 0:
            return bytes_data
        len_remain = len_wanted
        while len_remain != 0:
            try:
                tmp = await asyncio.wait_for(self._reader.read(len_remain), timeout=35.0)
            except asyncio.TimeoutError:
                print('TIMEOUT，稍后重连')
                self._writer.close()
                self.connected = False
                return None
            except :
                print(sys.exc_info()[0], sys.exc_info()[1])
                print('请联系开发者')
                self._writer.close()
                self.connected = False
                return None
                
            if not tmp:
                print("# FIN，稍后将重连")
                self._writer.close()
                self.connected = False
                return None
            else:
                bytes_data = bytes_data + tmp
                len_remain = len_remain - len(tmp)
                
        return bytes_data
        
    async def ReceiveMessageLoop(self):
        while self.connected == True:
            tmp = await self.ReadSocketData(16)
            if tmp is None:
                break
            
            expr, = struct.unpack('!I', tmp[:4])

            num, = struct.unpack('!I', tmp[8:12])

            num2 = expr - 16

            tmp = await self.ReadSocketData(num2)
            if tmp is None:
                break

            if num2 != 0:
                num -= 1
                if num == 0 or num == 1 or num == 2:
                    num3, = struct.unpack('!I', tmp)
                    self._UserCount = num3
                    continue
                elif num == 3 or num == 4:
                    try:
                        messages = tmp.decode('utf-8')
                    except:
                        continue
                    await self.parseDanMu(messages)
                    continue
                elif num == 5 or num == 6 or num == 7:
                    continue
                else:
                    if num != 16:
                        pass
                    else:
                        continue

   
    async def parseDanMu(self, messages):

        try:
            dic = json.loads(messages)
        except:
            return
        cmd = dic['cmd']

        if cmd == 'DANMU_MSG':
            # print(dic)
            Printer().printlist_append(['danmu', '弹幕', 'user', dic])
            return
        if cmd == 'SYS_GIFT':
            if 'giftId' in dic.keys():
                if str(dic['giftId']) in bilibili().get_giftids_raffle_keys():
                    
                    text1 = dic['real_roomid']
                    text2 = dic['url']
                    Printer().printlist_append(['join_lottery', '', 'user', "检测到房间{:^9}的{}活动抽奖".format(text1, bilibili().get_giftids_raffle(str(dic['giftId'])))], True)
                    await asyncio.sleep(random.uniform(3, 5))
                    bilibili().post_watching_history(text1)
                    result = utils.check_room_true(text1)
                    if True in result:
                        Printer().printlist_append(['join_lottery', '钓鱼提醒', 'user', "WARNING:检测到房间{:^9}的钓鱼操作".format(text1)], True)
                    else:
                        response = bilibili().get_giftlist_of_events(text1)
                        checklen = response.json()['data']
                        num = len(checklen)
                        for j in range(0, num):
                            await asyncio.sleep(random.uniform(0.5, 1))
                            resttime = response.json()['data'][j]['time']
                            raffleid = response.json()['data'][j]['raffleId']
                            if Statistics().check_activitylist(raffleid):

                                response1 = bilibili().get_gift_of_events_app(text1, text2, raffleid)
                                pc_response = bilibili().get_gift_of_events_web(text1, text2, raffleid)

                                
                                Printer().printlist_append(['join_lottery', '', 'user', "参与了房间{:^9}的{}活动抽奖".format(text1, bilibili().get_giftids_raffle(str(dic['giftId'])))], True)

                                json_response1 = response1.json()
                                json_pc_response = pc_response.json()
                                if json_response1['code'] == 0:
                                    Printer().printlist_append(['join_lottery', '', 'user', "# 移动端活动抽奖结果: ",
                                                                   json_response1['data']['gift_desc']])
                                    Statistics().add_to_result(*(json_response1['data']['gift_desc'].split('X')))
                                else:
                                    Printer().printlist_append(['join_lottery', '', 'user', "# 移动端活动抽奖结果: ", json_response1['message']])
                                    
                                    
                                Printer().printlist_append(
                                        ['join_lottery', '', 'user', "# 网页端活动抽奖状态: ", json_pc_response['message']])
                                if json_pc_response['code'] == 0:
                                    Statistics().append_to_activitylist(raffleid, text1)
                elif dic['giftId'] == 39:
                    Printer().printlist_append(['join_lottery', '', 'user', "节奏风暴"])
                    response = bilibili().get_giftlist_of_storm(dic)
                    temp = response.json()
                    check = len(temp['data'])
                    if check != 0 and temp['data']['hasJoin'] != 1:
                        id = temp['data']['id']
                        response1 = bilibili().get_gift_of_storm(id)
                        print(response1.json())
                    else:
                        Printer().printlist_append(['join_lottery','','debug', [dic, "请联系开发者"]])
                else:
                    text1 = dic['real_roomid']
                    text2 = dic['url']
                    Printer().printlist_append(['join_lottery', '', 'debug', [dic, "请联系开发者"]])
                    try:
                        Printer().printlist_append(['join_lottery', '', 'user', "检测到房间{:^9}的{}活动抽奖".format(text1, bilibili().get_giftids_raffle(str(dic['giftId'])))], True)
                        response = bilibili().get_giftlist_of_events(text1)
                        checklen = response.json()['data']
                        num = len(checklen)
                        for j in range(0, num):
                            await asyncio.sleep(random.uniform(0.5, 1))
                            resttime = response.json()['data'][j]['time']
                            raffleid = response.json()['data'][j]['raffleId']
                            if bilibili().check_activitylist(raffleid):
                                response1 = bilibili().get_gift_of_events_app(text1, text2, raffleid)
                                pc_response = bilibili().get_gift_of_events_web(text1, text2, raffleid)
                                Printer().printlist_append(['join_lottery', '', 'user', "参与了房间{:^9}的{}活动抽奖".format(text1, bilibili().get_giftids_raffle(str(dic['giftId'])))], True)
                                json_response1 = response1.json()
                                json_pc_response = pc_response.json()
                                if json_response1['code'] == 0:
                                    Printer().printlist_append(['join_lottery', '', 'user', "# 移动端活动抽奖结果: ",
                                                                   json_response1['data']['gift_desc']])
                                    Statistics().add_to_result(*(json_response1['data']['gift_desc'].split('X')))
                                else:
                                    Printer().printlist_append(['join_lottery', '', 'user', "# 移动端活动抽奖结果: ", json_response1['message']])
                                    
                                    
                                Printer().printlist_append(
                                        ['join_lottery', '', 'user', "# 网页端活动抽奖状态: ", json_pc_response['message']])
                                if json_pc_response['code'] == 0:
                                    Statistics().append_to_activitylist(raffleid, text1)
                                    
                                
                    except :
                        pass
                    
            else:
                Printer().printlist_append(['join_lottery', '普通送礼提示', 'user', ['普通送礼提示', dic['msg_text']]])
            return
        if cmd == 'SYS_MSG':
            if set(self.dic_bulletin) == set(dic):
                Printer().printlist_append(['join_lottery', '系统公告', 'user', dic['msg']])
            else:
                try:
                    TV_url = dic['url']
                    real_roomid = dic['real_roomid']
                    Printer().printlist_append(['join_lottery', '小电视', 'user', "检测到房间{:^9}的小电视抽奖".format(real_roomid)], True)
                    # url = "https://api.live.bilibili.com/AppSmallTV/index?access_key=&actionKey=appkey&appkey=1d8b6e7d45233436&build=5230003&device=android&mobi_app=android&platform=android&roomid=939654&ts=1521734039&sign=4f85e1d3ce0e1a3acd46fcf9ca3cbeed"
                    await asyncio.sleep(random.uniform(3, 5))
                    bilibili().post_watching_history(real_roomid)
                    result = utils.check_room_true(real_roomid)
                    if True in result:
                        Printer().printlist_append(['join_lottery', '钓鱼提醒', 'user', "WARNING:检测到房间{:^9}的钓鱼操作".format(real_roomid)], True)
                    else:
                        response = bilibili().get_giftlist_of_TV(real_roomid)
                        checklen = response.json()['data']['unjoin']
                        num = len(checklen)
                        for j in range(0, num):
                            await asyncio.sleep(random.uniform(0.5, 1))
                            resttime = response.json()['data']['unjoin'][j]['dtime']
                            raffleid = response.json()['data']['unjoin'][j]['id']
                            if Statistics().check_TVlist(raffleid):
                                response2 = bilibili().get_gift_of_TV(real_roomid, raffleid)
                                Statistics().append_to_TVlist(raffleid, real_roomid)
                                Printer().printlist_append(['join_lottery', '小电视', 'user', "参与了房间{:^9}的小电视抽奖".format(real_roomid)], True)
                                Printer().printlist_append(
                                    ['join_lottery', '小电视', 'user', "# 小电视道具抽奖状态: ", response2.json()['msg']])
                except:
                    pass
        if cmd == 'GUARD_MSG':
            print(dic)
            try:
                a = re.compile(r"(?<=在主播 )\S+(?= 的直播间开通了总督)")
                res = a.findall(str(dic))
                search_url = "https://search.bilibili.com/api/search?search_type=live&keyword=" + str(res[0])
                response = requests.get(search_url)
                roomid = response.json()['result']['live_user'][0]['roomid']
                print(roomid)
                response1 = bilibili().get_giftlist_of_captain(roomid)
                print(response1.json())
                num = len(response1.json()['data']['guard'])
                for i in range(0, num):
                    id = response1.json()['data']['guard'][i]['id']
                    print(id)
                    response2 = bilibili().get_gift_of_captain(roomid, id)
                    payload = {"roomid": roomid, "id": id, "type": "guard", "csrf_token": ''}
                    print(payload)
                    print("获取到房间 %s 的总督奖励: " %(roomid),response2.json())
            except:
                Printer().printlist_append(['join_lotter', '', 'debug', "# 没领取到奖励,请联系开发者"])
                pass
            return
