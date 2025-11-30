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

## 📋 요구사항

### Python 버전
- Python 3.9 이상

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

## 🔧 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/ict_autotrader.git
cd ict_autotrader
```

### 2. 가상환경 생성 및 활성화
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
# 프로덕션 의존성
pip install -r requirements.txt

# 개발 환경의 경우 추가로
pip install -r requirements-dev.txt
```

### 4. 환경 설정
```bash
# .env.example을 복사하여 .env 생성
cp .env.example .env

# .env 파일을 편집하여 API 키 입력
# BINANCE_TESTNET_API_KEY=your_testnet_api_key
# BINANCE_TESTNET_API_SECRET=your_testnet_api_secret
```

설정 파일(`config.yaml`)을 필요에 따라 수정합니다.

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

1. **테스트넷 사용 권장**: 처음 사용 시 반드시 Binance Testnet에서 테스트하세요.
2. **리스크 관리**: `config.yaml`의 위험 관리 파라미터를 신중하게 설정하세요.
3. **API 키 보안**: `.env` 파일을 절대 공개 저장소에 업로드하지 마세요.
4. **백업**: 중요한 거래 전 설정 파일과 로그를 백업하세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여

버그 리포트, 기능 제안, Pull Request를 환영합니다!

---

**생성일**: 2025-11-30
**마지막 업데이트**: 2025-11-30
