# -*- coding: utf-8 -*-
"""
[인빅투스 프리즘 연합 사령부]
제4호 클라우드 무기체계: 모바일 대시보드 암호화 빌더 (Dashboard Cryptographic Builder)
- 실시간 국내 4대 보유 전선 시세 및 글로벌 매크로 지표 수집
- 포트폴리오 종합 자산 가치 및 세력 수급 평가 연산
- 군사 보안급 AES-GCM 256-bit 암호화 페이로드(payload.json) 생성
"""

import os
import sys
import json
import logging
from datetime import datetime
import zoneinfo
import requests
import yfinance as yf
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DashboardBuilder")

KST = zoneinfo.ZoneInfo("Asia/Seoul")
DASHBOARD_PIN = os.getenv("DASHBOARD_PIN", "7777")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PAYLOAD_PATH = os.path.join(SCRIPT_DIR, "payload.json")

# 사령관님 포트폴리오 확정 팩트
PORTFOLIO_CONFIG = {
    "두산에너빌리티": {
        "code": "034020",
        "shares": 96,
        "avg_price": 85616,
        "support": "53,400원",
        "target": "65,000원",
        "badge": "원전/SMR 글로벌 인프라",
        "status": "쌍바닥 사수 완료 (저점 매집 완료)"
    },
    "LG전자": {
        "code": "066570",
        "shares": 16,
        "avg_price": 154495,
        "support": "145,000원",
        "target": "170,000원",
        "badge": "AI 데이터센터 냉각 칠러 & VS전장",
        "status": "기관/외인 바닥권 매집 지속"
    },
    "펄어비스": {
        "code": "263750",
        "shares": 222,
        "avg_price": 48547,
        "support": "34,000원",
        "target": "37,200원 / 37,500원 (예약매도 대기)",
        "badge": "붉은사막 DLC 글로벌 흥행",
        "status": "스팀 글로벌 TOP 10 랭크 & 사우디 심의 통과"
    },
    "SK바이오사이언스": {
        "code": "302440",
        "shares": 59,
        "avg_price": 47751,
        "support": "32,000원",
        "target": "42,000원",
        "badge": "사노피 21가 소아 폐렴구균 3상",
        "status": "바닥 지지력 강화 및 R&PD 센터 증설"
    }
}

RESERVED_CASH = 33914


def fetch_kr_stocks():
    """네이버 모바일 API 기반 실시간 시세 수집"""
    stocks = []
    total_eval = 0
    total_cost = 0
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for name, item in PORTFOLIO_CONFIG.items():
        code = item["code"]
        shares = item["shares"]
        avg_price = item["avg_price"]
        url = f"https://m.stock.naver.com/api/stock/{code}/basic"
        
        close_price = avg_price
        diff_price = 0
        ratio = 0.0
        
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                close_price = int(data.get("closePrice", str(avg_price)).replace(",", ""))
                diff_price = int(data.get("compareToPreviousClosePrice", "0").replace(",", ""))
                ratio = float(data.get("fluctuationsRatio", "0.0"))
        except Exception as e:
            logger.warning(f"시세 수집 오류 ({name}): {e}")
            
        eval_amt = close_price * shares
        cost_amt = avg_price * shares
        profit = eval_amt - cost_amt
        profit_rate = (profit / cost_amt * 100) if cost_amt > 0 else 0.0
        
        total_eval += eval_amt
        total_cost += cost_amt
        
        stocks.append({
            "name": name,
            "code": code,
            "shares": shares,
            "avg_price": avg_price,
            "close_price": close_price,
            "diff_price": diff_price,
            "ratio": ratio,
            "eval_amount": eval_amt,
            "cost_amount": cost_amt,
            "profit": profit,
            "profit_rate": round(profit_rate, 2),
            "support": item["support"],
            "target": item["target"],
            "badge": item["badge"],
            "status": item["status"]
        })
        
    total_profit = total_eval - total_cost
    total_profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0.0
    total_assets = total_eval + RESERVED_CASH
    
    return {
        "stocks": stocks,
        "total_eval": total_eval,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "total_profit_rate": round(total_profit_rate, 2),
        "reserved_cash": RESERVED_CASH,
        "total_assets": total_assets
    }


def fetch_macro_data():
    """Yahoo Finance 글로벌 매크로 지표 수집"""
    tickers = {
        "NASDAQ": ("^IXIC", "나스닥", "pt"),
        "S&P500": ("^GSPC", "S&P 500", "pt"),
        "SOX": ("^SOX", "반도체 SOX", "pt"),
        "USDKRW": ("USDKRW=X", "원/달러 환율", "원"),
        "WTI": ("CL=F", "WTI 원유", "$"),
        "US10Y": ("^TNX", "미 10년 국채", "%"),
        "NVDA": ("NVDA", "엔비디아", "$")
    }
    
    macro = []
    for key, (sym, label, unit) in tickers.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                prev = hist["Close"].iloc[-2]
                curr = hist["Close"].iloc[-1]
                pct = (curr - prev) / prev * 100
                diff = curr - prev
                macro.append({
                    "name": label,
                    "symbol": sym,
                    "value": round(float(curr), 2),
                    "diff": round(float(diff), 2),
                    "pct": round(float(pct), 2),
                    "unit": unit
                })
            elif len(hist) == 1:
                curr = hist["Close"].iloc[-1]
                macro.append({
                    "name": label,
                    "symbol": sym,
                    "value": round(float(curr), 2),
                    "diff": 0.0,
                    "pct": 0.0,
                    "unit": unit
                })
        except Exception as e:
            logger.warning(f"매크로 수집 실패 ({key}): {e}")
            
    return macro


def encrypt_payload(data_dict, pin):
    """AES-GCM 256비트 암호화 (브라우저 Web Crypto API와 100% 호환)"""
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(pin.encode("utf-8"))
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    plaintext = json.dumps(data_dict, ensure_ascii=False).encode("utf-8")
    ciphertext = aesgcm.encrypt(iv, plaintext, None)
    
    return {
        "salt": salt.hex(),
        "iv": iv.hex(),
        "ciphertext": ciphertext.hex(),
        "encrypted_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    }


def main():
    logger.info("==========================================")
    logger.info("[모바일 대시보드] 최신 암호화 페이로드 빌드 시작")
    logger.info("==========================================")
    
    now_kst = datetime.now(KST)
    logger.info(f"현재 KST 시각: {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 국내 4대 전선 수집
    holdings = fetch_kr_stocks()
    logger.info(f"국내 전선 수집 완료: 총 평가액 {holdings['total_eval']:,}원 (손익률 {holdings['total_profit_rate']}%)")
    
    # 2. 글로벌 매크로 수집
    macro = fetch_macro_data()
    logger.info(f"글로벌 매크로 수집 완료: {len(macro)}개 지표")
    
    # 3. 종합 페이로드 데이터 번들링
    payload_data = {
        "commander": "이정훈 사령관님",
        "system_name": "INVICTUS PRISM SENTINEL COMMAND CENTER",
        "updated_at": now_kst.strftime("%Y년 %m월 %d일 %H:%M KST"),
        "holdings": holdings,
        "macro": macro,
        "tactical_orders": [
            "두산에너빌리티: 53,400원 쌍바닥 사수 중이며 체코 본계약 모멘텀 대기. 투매 동참 절대 금지.",
            "LG전자: 145,000원 전후 기관 수급 방어선 확인. 빅테크 냉각 칠러 수주 지속 관찰.",
            "펄어비스: 붉은사막 DLC 글로벌 탑10 순항 중. 37,200원 / 37,500원 예약매도 모니터링 유지.",
            "SK바이오사이언스: 32,000원 강력한 바닥 지지선 확인. 소아 폐렴구균 3상 순항.",
            "자금 운용 수칙: 비상 탄약 33,914원은 완전 보존하며 뇌동매매를 엄격히 차단함."
        ]
    }
    
    # 4. AES-GCM 256-bit 군사급 암호화
    logger.info(f"AES-GCM 암호화 진행 (PIN 보호 체계)...")
    encrypted_bundle = encrypt_payload(payload_data, DASHBOARD_PIN)
    
    # 5. 파일 저장
    with open(OUTPUT_PAYLOAD_PATH, "w", encoding="utf-8") as f:
        json.dump(encrypted_bundle, f, ensure_ascii=False, indent=2)
        
    logger.info(f"암호화 페이로드 생성 완료: {OUTPUT_PAYLOAD_PATH}")
    logger.info("모바일 대시보드 빌드 작전이 완벽하게 완료되었습니다.")


if __name__ == "__main__":
    main()
