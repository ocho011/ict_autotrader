# ICT AutoTrader

Binance Futures 자동 매매 시스템 - ICT (Inner Circle Trader) 전략 기반

## 🚀 프로젝트 소개

ICT AutoTrader는 Michael Huddleston(ICT)의 트레이딩 개념을 기반으로 한 자동화된 암호화폐 선물 거래 시스템입니다.
Binance Futures API를 활용하여 Order Block, Fair Value Gap(FVG), Liquidity 등의 ICT 핵심 개념을 자동으로 감지하고 거래합니다.

## ✨ 주요 기능

- 📊 **ICT 패턴 자동 감지**: Order Block, FVG, Liquidity 패턴 실시간 탐지
- 🔄 **비동기 처리**: aiohttp 기반 고성능 비동기 데이터 수집 및 거래
- 🛡️ **리스크 관리**: 계정 잔고 대비 위험 비율 자동 계산 및 제한
- 🔔 **알림 시스템**: Discord webhook을 통한 실시간 거래 알림
- 🧪 **테스트넷 지원**: 안전한 전략 테스트를 위한 Binance Testnet 지원

## 🚀 Quick Start Guide

처음 사용하시는 분들을 위한 빠른 시작 가이드입니다.

### 1. Binance Testnet 계정 준비

실제 돈을 사용하지 않고 안전하게 테스트하기 위해 **Binance Testnet**을 사용합니다.

1. [Binance Testnet](https://testnet.binance.vision/) 방문
2. GitHub 계정으로 로그인
3. API 관리 페이지에서 API 키 생성
4. API Key와 Secret Key를 안전하게 보관

### 2. 프로젝트 설치

```bash
# 저장소 클론
git clone https://github.com/yourusername/ict_autotrader.git
cd ict_autotrader

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일을 편집하여 Binance Testnet API 키를 입력합니다:

```bash
# Testnet API Keys (for testing without real money)
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret_here

# Discord Webhook (optional)
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

### 4. 설정 확인

`config.yaml` 파일을 열어 다음 설정을 확인합니다:

```yaml
# ⚠️ CRITICAL: 반드시 testnet을 true로 유지하세요!
use_testnet: true

# 거래 페어 및 타임프레임
symbol: BTCUSDT
interval: 15m  # 15분 캔들

# 리스크 관리 (신중하게 설정)
risk_per_trade: 0.02  # 거래당 2% 위험
max_daily_loss_percent: 0.05  # 일일 최대 5% 손실
max_position_percent: 0.10  # 최대 10% 포지션
max_trades_per_day: 5  # 하루 최대 거래 수
```

### 5. 봇 실행

```bash
# 봇 시작
python -m src.main
```

정상 작동 시 다음과 같은 로그가 출력됩니다:
```
INFO  | Starting ICT Auto Trader MVP...
INFO  | Symbol: BTCUSDT
INFO  | Interval: 15m
INFO  | Testnet: True
INFO  | WebSocket connected to Binance Testnet
```

### 6. 로그 모니터링

봇이 실행되는 동안 다음 정보를 확인할 수 있습니다:

- **패턴 감지**: Order Block, FVG 등의 ICT 패턴 탐지
- **신호 발생**: 매수/매도 진입 신호
- **주문 실행**: 실제 주문 내역 및 결과
- **Discord 알림** (설정 시): 거래 알림이 Discord로 전송

로그 파일 위치: `logs/trader.log`

## 📋 요구사항

### Python 버전
- Python 3.10 이상 (권장: Python 3.11+)

### Binance Testnet 계정
- [Binance Testnet](https://testnet.binance.vision/)에서 무료로 생성 가능
- GitHub 계정으로 간편 로그인
- Testnet USDT는 무료로 제공 (실제 돈 불필요)

### 의존성 패키지

#### 프로덕션 의존성 (`requirements.txt`)
```bash
pip install -r requirements.txt
```

주요 패키지:
- `python-binance>=1.0.19` - Binance API 통합
- `python-dotenv>=1.0.0` - 환경 변수 관리
- `pyyaml>=6.0` - 설정 파일 파싱
- `aiohttp>=3.9.0` - 비동기 HTTP 클라이언트
- `loguru>=0.7.0` - 로깅 프레임워크
- `pydantic>=2.0.0` - 데이터 검증 및 설정 관리

#### 개발 의존성 (`requirements-dev.txt`)
```bash
pip install -r requirements-dev.txt
```

개발 도구:
- `pytest>=8.0.0` - 테스트 프레임워크
- `pytest-asyncio>=0.23.0` - 비동기 테스트 지원
- `black>=24.0.0` - 코드 포맷터
- `flake8>=7.0.0` - 린터
- `mypy>=1.8.0` - 타입 체커

## 🔧 개발 환경 설정 (선택사항)

개발에 기여하시거나 고급 기능을 사용하시려면:

```bash
# 개발 의존성 추가 설치
pip install -r requirements-dev.txt

# 코드 품질 검사
black src/ tests/       # 코드 포맷팅
flake8 src/ tests/      # 린팅
mypy src/               # 타입 체킹
```

## 📁 프로젝트 구조

```
ict_autotrader/
├── src/                    # 소스 코드
│   ├── core/              # 핵심 비즈니스 로직
│   ├── data/              # 데이터 수집 및 처리
│   ├── strategy/          # ICT 전략 구현
│   ├── execution/         # 주문 실행 로직
│   └── notification/      # 알림 시스템
├── tests/                 # 테스트 코드
│   ├── unit/             # 단위 테스트
│   ├── integration/      # 통합 테스트
│   └── fixtures/         # 테스트 픽스처
├── docs/                  # 프로젝트 문서
├── logs/                  # 로그 파일
├── .env.example          # 환경 변수 템플릿
├── config.yaml           # 설정 파일
├── requirements.txt      # 프로덕션 의존성
└── requirements-dev.txt  # 개발 의존성
```

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest tests/

# 커버리지 포함 테스트
pytest tests/ --cov=src --cov-report=html

# 특정 테스트 파일 실행
pytest tests/test_config.py -v
```

## 📚 문서

- [Architecture Guide](docs/architecture.md) - 시스템 아키텍처 설명
- [Testing Guide](docs/testing.md) - 테스트 전략 및 방법
- [Configuration Guide](docs/CONFIGURATION_GUIDE.md) - 설정 파일 가이드
- [Development Workflow](docs/WORKFLOW.md) - 개발 워크플로우

## ⚠️ 주의사항

### 🔴 필수 주의사항

1. **테스트넷에서 먼저 테스트**
   - 실제 거래 전 **최소 2주간** Testnet에서 안정성 검증
   - `config.yaml`의 `use_testnet: true` 설정 확인
   - Mainnet 전환 시 작은 금액부터 시작

2. **리스크 관리 철저**
   - `risk_per_trade`: 1-2% 권장 (절대 5% 이상 X)
   - `max_daily_loss_percent`: 3-5% 권장
   - `max_trades_per_day`: 과도한 거래 방지

3. **API 키 보안**
   - `.env` 파일을 **절대 공개 저장소에 업로드 금지**
   - `.gitignore`에 `.env` 포함 여부 확인
   - Mainnet API 키는 IP 제한 설정 권장

4. **모니터링 및 백업**
   - 거래 시작 전 Discord 알림 테스트
   - 로그 파일(`logs/`) 정기적으로 확인
   - 설정 파일 백업 (`config.yaml`, `.env`)

### ⚡ 일반적인 문제 해결

**Q: "WebSocket connection failed" 에러가 발생합니다**
```bash
# API 키 확인
cat .env  # Testnet 키가 올바른지 확인

# 네트워크 연결 확인
ping testnet.binance.vision

# 방화벽 설정 확인
# Binance Testnet 웹소켓 포트(9443) 개방 필요
```

**Q: "Insufficient balance" 에러**
```bash
# Testnet 잔고 확인 및 충전
# https://testnet.binance.vision/ 에서 Faucet 사용
# 무료로 Testnet USDT 지급받기
```

**Q: 봇이 신호를 생성하지 않습니다**
```bash
# 로그 확인
tail -f logs/trader.log

# 최소 캔들 수 확인 (최소 20개 캔들 필요)
# 15분 봉 기준 약 5시간 대기 필요
```

**Q: Discord 알림이 오지 않습니다**
```bash
# Webhook URL 확인
# Discord 서버 설정 > 통합 > 웹후크
# .env의 DISCORD_WEBHOOK_URL이 올바른지 확인
```

## 🤝 기여하기

ICT AutoTrader 프로젝트에 기여해 주셔서 감사합니다!

### 기여 방법

1. **버그 리포트**
   - GitHub Issues에 상세한 버그 설명 작성
   - 재현 가능한 단계 제공
   - 로그 파일 첨부 (민감한 정보 제거 후)

2. **기능 제안**
   - GitHub Issues에 기능 제안서 작성
   - 사용 사례 및 예상 효과 설명

3. **Pull Request**
   ```bash
   # Fork 후 브랜치 생성
   git checkout -b feature/your-feature-name

   # 코드 작성 및 테스트
   pytest tests/

   # 코드 품질 검사
   black src/ tests/
   flake8 src/ tests/

   # Pull Request 제출
   ```

### 개발 가이드라인

- 코드 스타일: Black 포맷터 사용
- 테스트: 새 기능은 반드시 테스트 코드 포함
- 문서화: 주요 함수와 클래스에 docstring 작성
- 커밋 메시지: 명확하고 설명적으로 작성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원 및 문의

- **이슈 트래킹**: [GitHub Issues](https://github.com/yourusername/ict_autotrader/issues)
- **개발 문서**: [docs/](docs/) 디렉토리 참조
- **PRD 문서**: [.taskmaster/docs/ict-autotrader-mvp-prd.md](.taskmaster/docs/ict-autotrader-mvp-prd.md)

---

**⚠️ 면책조항**: 이 소프트웨어는 교육 및 연구 목적으로 제공됩니다. 실제 거래에 사용할 경우 발생하는 모든 손실에 대해 개발자는 책임을 지지 않습니다. 자동매매 시스템 사용 전 충분한 이해와 테스트가 필요합니다.

**생성일**: 2025-11-30
**마지막 업데이트**: 2025-12-01
