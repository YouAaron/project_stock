import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import time
import sys

# ----------------------------------------------------
# 1. 콘솔 출력 인코딩 설정 (한글 깨짐 및 에러 방지)
# ----------------------------------------------------
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ----------------------------------------------------
# 2. API Key 및 기본 설정 (코드 내 저장)
# ----------------------------------------------------
# ⚠️ 본인의 Upstage API 키를 여기에 입력해 주세요.
UPSTAGE_API_KEY = "up_Y7OKHBUB2q7pi7C4E1ILIWItBAUOG"

SECTIONS = {"101": "경제"}  # 주식/종목 분석용 경제 섹션
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ----------------------------------------------------
# 3. 크롤링 관련 함수들
# ----------------------------------------------------
def fetch_article_content(article_url):
    """기사 상세 URL에 접속하여 본문 텍스트 추출"""
    try:
        response = requests.get(article_url, headers=HEADERS)
        if response.status_code != 200:
            return "본문 접속 실패"
        soup = BeautifulSoup(response.text, "html.parser")
        content_target = soup.find(id="dic_area")
        if content_target:
            return content_target.get_text(strip=True)
        return "본문 태그를 찾을 수 없음"
    except Exception as e:
        return f"본문 수집 중 에러 발생: {e}"

def fetch_naver_news_by_page(sid1, section_name, page_num):
    """페이지별 기사 목록 및 본문 수집"""
    url = f"https://news.naver.com/main/list.naver?mode=LSD&sid1={sid1}&page={page_num}"
    news_list = []
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return news_list
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select(".list_body ul li")
        
        for article in articles:
            dt_tags = article.find_all("dt")
            if not dt_tags:
                continue
            
            a_tag = dt_tags[-1].find("a")
            if a_tag:
                title = a_tag.get_text(strip=True)
                link = a_tag["href"]
                writing_tag = article.find("span", class_="writing")
                writing = writing_tag.get_text(strip=True) if writing_tag else "알 수 없음"
                
                content = fetch_article_content(link)
                news_list.append({
                    "title": title,
                    "link": link,
                    "press": writing,
                    "content": content
                })
                time.sleep(0.3)  # 차단 방지 delay
    except Exception as e:
        pass
    return news_list

def crawl_naver_news(start_page, end_page):
    """전체 크롤링 실행 함수"""
    all_news = []
    for sid1, section_name in SECTIONS.items():
        for page in range(start_page, end_page + 1):
            page_news = fetch_naver_news_by_page(sid1, section_name, page)
            all_news.extend(page_news)
            time.sleep(0.5)
    return all_news

# ----------------------------------------------------
# 4. Upstage AI 주식 시장 종합 분석 함수
# ----------------------------------------------------
def analyze_market_summary(news_list):
    """뉴스 리스트를 받아 AI 종합 분석을 수행"""
    client = OpenAI(
        api_key=UPSTAGE_API_KEY,
        base_url="https://api.upstage.ai/v1/solar"
    )
    combined_news = "\n".join([f"- {news}" for news in news_list])
    
    try:
        response = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 증권가의 날카로운 주식 분석가입니다. "
                        "사용자가 제공한 여러 개의 뉴스 기사/요약을 모두 분석한 뒤, "
                        "**단 하나의 문장(또는 아주 짧은 2~3줄의 단락)**으로 "
                        "어떤 종목이 오를지, 내릴지, 보합일지 종합해서 설명해주세요. "
                        "각 종목별 이유는 괄호를 이용하거나 아주 짧은 구절로 핵심만 덧붙이세요. "
                        "예시 형식: 'A전자(실적 호조)와 D자동차(사전예약 돌파)는 상승하고, B바이오(임상 실패)는 하락할 것으로 보입니다.'"
                    )
                },
                {
                    "role": "user",
                    "content": f"다음 수집된 뉴스들을 종합해서 어떤 종목이나 업종이 오르고 내릴지 한 문장으로 요약해줘:\n\n{combined_news}"
                }
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Upstage API 분석 중 오류가 발생했습니다: {e}"

# ----------------------------------------------------
# 5. Streamlit 웹 Frontend 화면 구성
# ----------------------------------------------------
st.set_page_config(page_title="주식 뉴스 AI 종합 분석기", page_icon="📈", layout="centered")

st.title("📈 주식 뉴스 AI 종합 분석기")
st.markdown("네이버 실시간 경제 뉴스를 크롤링하여 **Upstage AI**가 시장 향방을 한 문장으로 요약해 드립니다.")
st.divider()

st.subheader("⚙️ 옵션 설정")
page_count = st.number_input(
    "수집할 뉴스 페이지 수 (1페이지당 약 20개 기사 수집)", 
    min_value=1, 
    max_value=5, 
    value=1
)

# 분석 시작 버튼
if st.button("뉴스 수집 및 AI 분석 시작", type="primary"):
    # 1단계: 뉴스 크롤링
    with st.spinner(f"네이버 경제 뉴스 {page_count}페이지를 수집 중입니다... (약 10~30초 소요)"):
        crawled_result = crawl_naver_news(start_page=1, end_page=page_count)
    
    # 2단계: AI 전달용 데이터 정제
    news_for_ai = []
    for item in crawled_result:
        if item['content'] and "실패" not in item['content'] and "찾을 수 없음" not in item['content']:
            # 기사 제목 + 본문 앞 300자 추출 (토큰 절약 및 정밀도 향상)
            news_for_ai.append(f"제목: {item['title']} / 본문: {item['content'][:300]}")
    
    if not news_for_ai:
        st.error("수집된 정상적인 뉴스가 없습니다. 잠시 후 다시 시도해 주세요.")
    else:
        st.success(f"총 {len(news_for_ai)}개의 기사를 성공적으로 수집했습니다!")
        
        # 3단계: Upstage AI 요약 및 분석
        with st.spinner("Upstage AI가 뉴스를 다각도로 분석 중입니다..."):
            ai_summary = analyze_market_summary(news_for_ai)
        
        # 결과 표시
        st.divider()
        st.subheader("💡 AI 주식 시장 종합 전망")
        st.info(ai_summary)
        
        # 참고 뉴스 접기/펴기 아코디언 메뉴
        with st.expander("🔍 분석에 사용된 수집 뉴스 목록 보기"):
            for idx, news in enumerate(crawled_result, 1):
                st.markdown(f"**{idx}. [{news['press']}]** [{news['title']}]({news['link']})")
