import streamlit as st
import time
import hmac
import hashlib
import base64
import requests
import urllib.parse
from bs4 import BeautifulSoup

# --- 1. API 키 세팅 (발급받은 키를 여기에 입력하세요) ---
API_KEY = "01000000005c40f92b3e6cb8c868e4a48fdec1ff3124bea1267148cffbc7901c79ec92f48c"
SECRET_KEY = "AQAAAABcQPkrPmy4yGjkpI/ewf8xfbEV1YjyQs3NjZLbngzkyQ=="
CUSTOMER_ID = "4534331"

BASE_URL = "https://api.naver.com"
STORE_NAME = "육향"
TARGET_KEYWORDS = ["가산맛집", "가산점심", "가산디지털단지맛집", "가산동곰탕", "육향"]

# --- 2. 데이터 수집 함수 ---
def generate_signature(timestamp, method, path, secret_key):
    sign = f"{timestamp}.{method}.{path}"
    signature = hmac.new(secret_key.encode('utf-8'), sign.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(signature).decode('utf-8')

@st.cache_data(ttl=3600) # 1시간 동안 데이터 캐싱 (API 과부하 방지)
def get_keyword_volume(keywords):
    path = "/keywordstool"
    timestamp = str(int(time.time() * 1000))
    signature = generate_signature(timestamp, "GET", path, SECRET_KEY)
    
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": API_KEY,
        "X-Customer": str(CUSTOMER_ID),
        "X-Signature": signature
    }
    
    hint_keywords = ",".join([k.replace(" ", "") for k in keywords])
    url = f"{BASE_URL}{path}?hintKeywords={hint_keywords}&showDetail=1"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('keywordList', [])
    return []

@st.cache_data(ttl=3600)
def get_place_ranking(keyword, store_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
    }
    encoded_keyword = urllib.parse.quote(keyword)
    
    total_rank = 0
    for page in range(1, 6): 
        url = f"https://m.map.naver.com/search2/search.naver?query={encoded_keyword}&page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            items = soup.select('li._item .item_title .name')
            if not items:
                break
            
            for item in items:
                total_rank += 1
                if store_name in item.text:
                    return total_rank 
        except Exception:
            pass
            
    return 0

# --- 3. 모바일 앱 화면(UI) 구성 ---
st.set_page_config(page_title="육향 대시보드", page_icon="📈", layout="centered")

st.title("📈 육향 마케팅 대시보드")
st.markdown("가산디지털단지 한라원앤원타워 매장 실시간 지표")

if st.button("🔄 데이터 최신화 (새로고침)"):
    st.cache_data.clear()

st.divider()

# 검색량 데이터 렌더링
st.subheader("🔥 핵심 키워드 월간 검색량")
if API_KEY == "여기에_액세스라이선스_입력":
    st.warning("코드 최상단에 API 키 3개를 입력해 주세요.")
else:
    with st.spinner("네이버 광고 서버에서 검색량을 가져오는 중..."):
        volumes = get_keyword_volume(TARGET_KEYWORDS)
        
        for data in volumes:
            kw = data.get('relKeyword')
            pc = data.get('monthlyPcQcCnt', 0)
            mo = data.get('monthlyMobileQcCnt', 0)
            pc = 0 if isinstance(pc, str) else pc
            mo = 0 if isinstance(mo, str) else mo
            total = pc + mo
            
            # 모바일 앱에 어울리는 카드 형태의 UI
            st.metric(label=f"🔍 {kw}", value=f"{total:,}회", delta=f"모바일: {mo:,}회 / PC: {pc:,}회", delta_color="off")

st.divider()

# 플레이스 순위 렌더링
st.subheader("🏆 네이버 스마트플레이스 순위")
st.caption("모바일 통합검색 기준 순위입니다.")

with st.spinner("플레이스 노출 순위를 추적하는 중..."):
    for kw in ["가산디지털단지맛집", "가산디지털단지역맛집"]:
        rank = get_place_ranking(kw, STORE_NAME)
        
        if rank > 0:
            st.success(f"**{kw}** 검색 시 👉 **{rank}위** 노출 중")
        elif rank == 0:
            st.error(f"**{kw}** 검색 시 👉 상위 노출 리스트에 없습니다.")
        else:
            st.warning(f"**{kw}** 검색 시 👉 순위 조회 실패 (네이버 로딩 지연)")
