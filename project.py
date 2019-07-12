# -*- coding: utf-8 -*-
import re
import urllib.request

from bs4 import BeautifulSoup

from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter

import xml.etree.ElementTree as ET


SLACK_TOKEN = "xoxb-689115425012-678323281795-r2aZiWW4IXH4qRDOzxJS5r7Z"
SLACK_SIGNING_SECRET = "0d11959f3fe2399e4d51dc1c860d5e65"


app = Flask(__name__)
slack_events_adaptor = SlackEventAdapter(SLACK_SIGNING_SECRET, "/listening", app)
slack_web_client = WebClient(token=SLACK_TOKEN)

dicNo = {} # 버스 번호를 key로 갖고 버스 아이디를 value로 갖는 딕셔너리 자료형 선언
rc = '' # 현재 정류장아이디 저장(현재 정류장 부터 종점까지 출력하기 위해서) 

def bus_info(text):
   global rc
   global dicNo
   url_match = re.search(r'\d{1,}', text)
   if not url_match:
       return('올바른 값을 입력해주세요.')
   text_list = text.split()
   result = []

   if len(text_list[1]) > 4:  # 입력 값 -> 버스정류장ID
       # 버스번호 출력
       static_url = 'http://openapitraffic.daejeon.go.kr/api/rest/arrive/getArrInfoByUid?arsId='
       serviceKey = '&serviceKey=wU25sEMMnY1Vw82mv%2FcrSIs0QGLAygNDPzN656edxTh28O3uh8jMBR4I3DC6TUosgRzAdKABwBCZDMU4aJgNUw%3D%3D'

       url = static_url + text_list[1] + serviceKey # 공공데이터포털에 요청할 URL조합

       tree = ET.parse(urllib.request.urlopen(url)) # XML파싱
       tag = tree.find('msgBody')
       result.append("현 위치 : " + tag[0].find("STOP_NAME").text + " \n")
       for page in list(tag): # 출력할 텍스트 조합
           sn = page.find("STOP_NAME").text
           rn = page.find("ROUTE_NO").text
           cd = page.find("ROUTE_CD").text
           dicNo[rn] = cd
           sp = page.find("STATUS_POS").text
           em = page.find("EXTIME_MIN").text
           result.append(rn + " 번 버스" + "\t[ " + em + "분 후 도착 ] " + "\t<" + sp + " 정거장 전>")
           rc = page.find("BUS_NODE_ID").text

   elif len(text_list[1]) <= 4:  # 입력 값 -> 버스번호

        # 버스노선출력
        static_url2 = "http://openapitraffic.daejeon.go.kr/api/rest/busRouteInfo/getStaionByRoute?busRouteId="
        service_key2 = "&serviceKey=wU25sEMMnY1Vw82mv%2FcrSIs0QGLAygNDPzN656edxTh28O3uh8jMBR4I3DC6TUosgRzAdKABwBCZDMU4aJgNUw%3D%3D"
        url2 = static_url2 + str(dicNo[text_list[1]]) + service_key2 # 공공데이터포털에 요청할 URL조합

        tree2 = ET.parse(urllib.request.urlopen(url2)) # XML파싱
        tag2 = tree2.find('msgBody')
        bt = ""# 한 버스의 총 노선 중 현재 정류장의 순서를 저장하기 위한 변수

        for page2 in list(tag2):
            if (rc == page2.find("BUS_NODE_ID").text): # 총 노선 중 현재 정류장의 순서 비교
                bt = page2.find("BUSSTOP_SEQ").text # 현재 정류장의 순서를 찾으면 bt 변수에 저장
            else:
                pass

        for page2 in list(tag2):
            if (bt == page2.find("BUSSTOP_SEQ").text):
                result.append("★ 현 위치 :" + page2.find("BUSSTOP_NM").text + " ★\n")
                bt = page2.find("BUSSTOP_SEQ").text
            elif (int(page2.find("BUSSTOP_SEQ").text) > int(bt)):
                result.append(" - " + page2.find("BUSSTOP_NM").text + "\n")
        # pass

   return u'\n'.join(result)


# 챗봇이 멘션을 받았을 경우
@slack_events_adaptor.on("app_mention")
def app_mentioned(event_data):
   channel = event_data["event"]["channel"]
   text = event_data["event"]["text"]

   message = bus_info(text)
   slack_web_client.chat_postMessage(
       channel=channel,
       text=message
   )


# / 로 접속하면 서버가 준비되었다고 알려줍니다.
@app.route("/", methods=["GET"])
def index():
   return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
   app.run('0.0.0.0', port=5000)