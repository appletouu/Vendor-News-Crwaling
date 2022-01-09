from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
import gspread_dataframe as gd
from gspread_formatting import *
import requests
import os
from bs4 import BeautifulSoup
from datetime import timedelta, datetime
import pandas as pd
import re

#사용할 시트 ID
SPREADSHEET_ID = os.getenv("peaches_one_universe")
#나의 권한 Key
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("NO_TRESPASSING_APPLE_ONLY")

#어떤 권한이 필요한지
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

#Key를 사용해서 권한 정보를 통합 생성
#creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_APPLICATION_CREDENTIALS, scope)
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_APPLICATION_CREDENTIALS, strict=False), scope)

#구글 스프레드시트 연동 + 시트 열기
gc = gspread.authorize(creds)

keywords = os.getenv("KEYWORDS", "마이크로소프트,VMware,델 테크놀로지스,클라우데라").split(',')
sortType = os.getenv("SORT_TYPE", 0)
today_str = datetime.today().strftime("%Y%m%d")
today_num = int(today_str)


for keyword in keywords:
    response = requests.get(f'https://search.naver.com/search.naver?where=news&query={keyword}&sort={sortType}')
    soup = BeautifulSoup(response.text, 'html.parser')

    Title = []
    Press_name = []
    News_date = []
    Link = []

    for news_result in soup.select(".list_news > li"):

        title = news_result.select_one(".news_tit").text
        press_name = news_result.select_one(".info.press").text
        link = news_result.select_one(".news_tit")["href"]
        news_dates = news_result.select('span.info')
        # (A면1단, 날짜) 형태로 되어 있는 경우 처리
        if len(news_dates) > 1 :
          news_date = news_dates[1].get_text().replace('.', '')
        else :
          news_date = news_dates[0].get_text().replace('.', '')
        
        if  "분" in news_date or "시간 전" in news_date :  
          news_date = str(today_num)
          news_date = datetime.strptime(news_date, '%Y%m%d').strftime('%Y-%m-%d')

        elif "일 전" in news_date :
          news_date_num = int(re.sub('[\D]', '', news_date))
          news_date = str(datetime.today() - timedelta(days=news_date_num))
          news_date = news_date[:10]
         # news_date = datetime.strptime(news_date, '%Y%m%d').strftime('%Y-%m-%d')
                
        else :
          news_date = str(news_date)
          news_date = datetime.strptime(news_date, '%Y%m%d').strftime('%Y-%m-%d')

        Title.append(title)
        Press_name.append(press_name)
        Link.append(link)
        News_date.append(news_date)


    news_data = pd.DataFrame(
    {
    '제목' : Title,
    '매체명' : Press_name,
    '날짜' : News_date,
    '링크' : Link})

    try:
      ws = gc.open_by_key(SPREADSHEET_ID).worksheet(keyword)
    except:
      ws = gc.open_by_key(SPREADSHEET_ID).add_worksheet(title=keyword, rows="1000", cols="10")

    #새로운 크롤링 데이터 가져와서
    existing_news = gd.get_as_dataframe(ws, parse_dates=True, usecols=[0,1,2,3], skiprows=1, header=None).dropna(0, 'all')


    updated = existing_news.append(news_data)

    #중복검사
    updated.drop_duplicates(subset=['링크'])
    gd.set_with_dataframe(ws, news_data)

    ws.format('1', {'textFormat': {'bold': True}})
    set_column_widths(ws, [ ('A', 500), ('D:', 500) ])

