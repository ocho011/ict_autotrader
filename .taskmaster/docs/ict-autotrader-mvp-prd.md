# ICT Auto Trader - MVP PRD
## 바이낸스 USDT 무기한 선물 자동매매 시스템 (축소 버전)

**문서 버전**: v1.0 (MVP)  
**작성일**: 2025-01-XX  
**목표 기간**: 3-4주  

---

## 1. MVP 철학

### 1.1 핵심 원칙

```
"일단 동작하는 것" > "완벽한 설계"

- 최소한의 기능으로 실제 트레이딩 가능한 상태 달성
- 이벤트 기반 설계로 확장성 확보 (단, 과도한 복잡성 배제)
- 필요할 때 확장 (YAGNI: You Aren't Gonna Need It)
```

### 1.2 MVP 범위

| 포함 ✅ | 제외 ❌ (확장 시 추가) |
|---------|------------------------|
| 전략 2개: Order Block + FVG | Market Structure 독립 모듈 |
| 타임프레임 1개 (15m) | 다중 타임프레임 |
| 심볼 1개 (BTCUSDT) | 다중 심볼 |
| 단순 이벤트 버스 | 다중 큐 + 워커 풀 |
| Discord 알림 | React GUI 대시보드 |
| 단일 config.yaml | 설정 분리 + 런타임 변경 |
| Testnet 거래 | Mainnet (테스트 완료 후) |
| 터미널 로그 | 웹 모니터링 |

### 1.3 목표

```
Week 1: 데이터 수집 + 이벤트 기반 구조
Week 2: OB/FVG 탐지 + 신호 생성
Week 3: 주문 실행 + 리스크 관리
Week 4: 테스트 + 안정화
```

---

## 2. 시스템 아키텍처

### 2.1 단순화된 이벤트 기반 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                     ICT Auto Trader MVP                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │  WebSocket  │────▶│   Event     │────▶│  Strategy   │      │
│   │   Client    │     │    Bus      │     │   Engine    │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
│                              │                   │              │
│                              │                   │              │
│                              ▼                   ▼              │
│                       ┌─────────────┐     ┌─────────────┐      │
│                       │   State     │     │   Order     │      │
│                       │   Store     │     │   Manager   │      │
│                       └─────────────┘     └─────────────┘      │
│                                                  │              │
│                                                  ▼              │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │   Logger    │◀────│   Discord   │◀────│    Risk     │      │
│   │             │     │   Notifier  │     │   Manager   │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 이벤트 흐름

```
1. WebSocket에서 캔들 데이터 수신
2. CANDLE_CLOSED 이벤트 발행
3. Strategy Engine이 구독하여 패턴 분석
4. 패턴 발견 시 SIGNAL 이벤트 발행
5. Order Manager가 구독하여 주문 실행
6. 주문 결과 TRADE 이벤트 발행
7. Discord로 알림 전송
```

### 2.3 이벤트 타입 (MVP)

```python
from enum import Enum

class EventType(Enum):
    # Data
    CANDLE_CLOSED = "candle_closed"
    
    # Pattern
    ORDER_BLOCK_DETECTED = "order_block_detected"
    FVG_DETECTED = "fvg_detected"
    
    # Trading
    ENTRY_SIGNAL = "entry_signal"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    POSITION_CLOSED = "position_closed"
    
    # System
    ERROR = "error"
```

---

## 3. 핵심 컴포넌트 상세

### 3.1 Event Bus (단순 버전)

> 복잡한 큐/워커 대신 단순 pub/sub 패턴

```python
# src/core/event_bus.py

import asyncio
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class EventBus:
    """단순 비동기 이벤트 버스"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """이벤트 구독"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    async def publish(self, event: Event):
        """이벤트 발행 (논블로킹)"""
        await self._queue.put(event)
    
    async def start(self):
        """이벤트 처리 루프 시작"""
        self._running = True
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._queue.get(), 
                    timeout=1.0
                )
                await self._dispatch(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event dispatch error: {e}")
    
    async def _dispatch(self, event: Event):
        """이벤트를 구독자들에게 전달"""
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    def stop(self):
        self._running = False
```

### 3.2 WebSocket Client

```python
# src/data/websocket_client.py

import asyncio
import json
from binance import AsyncClient, BinanceSocketManager

class BinanceWebSocket:
    def __init__(self, event_bus: EventBus, symbol: str, interval: str):
        self.event_bus = event_bus
        self.symbol = symbol
        self.interval = interval
        self.client = None
        self.bsm = None
    
    async def connect(self):
        """바이낸스 웹소켓 연결"""
        self.client = await AsyncClient.create(
            api_key=settings.api_key,
            api_secret=settings.api_secret,
            testnet=settings.use_testnet
        )
        self.bsm = BinanceSocketManager(self.client)
    
    async def start_kline_stream(self):
        """캔들 스트림 시작"""
        async with self.bsm.kline_futures_socket(
            symbol=self.symbol, 
            interval=self.interval
        ) as stream:
            while True:
                msg = await stream.recv()
                await self._handle_kline(msg)
    
    async def _handle_kline(self, msg: dict):
        """캔들 데이터 처리"""
        kline = msg['k']
        
        # 캔들 마감 시에만 이벤트 발행
        if kline['x']:  # is_closed
            candle = {
                'timestamp': kline['t'],
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v']),
            }
            
            await self.event_bus.publish(Event(
                type=EventType.CANDLE_CLOSED,
                data={'candle': candle, 'symbol': self.symbol}
            ))
```

### 3.3 State Store

```python
# src/core/state_store.py

from dataclasses import dataclass, field
from typing import List, Optional
from collections import deque

@dataclass
class OrderBlock:
    type: str  # 'bullish' or 'bearish'
    top: float
    bottom: float
    timestamp: int
    touches: int = 0
    is_valid: bool = True

@dataclass
class FVG:
    type: str  # 'bullish' or 'bearish'
    top: float
    bottom: float
    timestamp: int
    filled_percent: float = 0.0
    is_valid: bool = True

@dataclass 
class Position:
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    size: float
    stop_loss: float
    take_profit: float
    timestamp: int

class StateStore:
    """패턴 및 포지션 상태 관리"""
    
    def __init__(self, max_candles: int = 200):
        self.candles: deque = deque(maxlen=max_candles)
        self.order_blocks: List[OrderBlock] = []
        self.fvgs: List[FVG] = []
        self.current_position: Optional[Position] = None
        self.daily_pnl: float = 0.0
        self.trade_count: int = 0
    
    def add_candle(self, candle: dict):
        self.candles.append(candle)
    
    def add_order_block(self, ob: OrderBlock):
        self.order_blocks.append(ob)
        self._cleanup_old_patterns()
    
    def add_fvg(self, fvg: FVG):
        self.fvgs.append(fvg)
        self._cleanup_old_patterns()
    
    def _cleanup_old_patterns(self, max_age_candles: int = 100):
        """오래된 패턴 제거"""
        if len(self.candles) < max_age_candles:
            return
        
        cutoff_time = self.candles[-max_age_candles]['timestamp']
        self.order_blocks = [
            ob for ob in self.order_blocks 
            if ob.timestamp > cutoff_time and ob.is_valid
        ]
        self.fvgs = [
            fvg for fvg in self.fvgs 
            if fvg.timestamp > cutoff_time and fvg.is_valid
        ]
    
    def get_valid_order_blocks(self, ob_type: str = None) -> List[OrderBlock]:
        obs = [ob for ob in self.order_blocks if ob.is_valid]
        if ob_type:
            obs = [ob for ob in obs if ob.type == ob_type]
        return obs
    
    def get_valid_fvgs(self, fvg_type: str = None) -> List[FVG]:
        fvgs = [fvg for fvg in self.fvgs if fvg.is_valid]
        if fvg_type:
            fvgs = [fvg for fvg in fvgs if fvg.type == fvg_type]
        return fvgs
```

### 3.4 Strategy Engine (MVP: OB + FVG)

```python
# src/strategy/signal_engine.py

class SignalEngine:
    def __init__(self, event_bus: EventBus, state: StateStore, config: dict):
        self.event_bus = event_bus
        self.state = state
        self.config = config
        
        # 이벤트 구독
        self.event_bus.subscribe(EventType.CANDLE_CLOSED, self.on_candle_closed)
    
    async def on_candle_closed(self, event: Event):
        """캔들 마감 시 분석 실행"""
        candle = event.data['candle']
        self.state.add_candle(candle)
        
        # 최소 캔들 수 체크
        if len(self.state.candles) < 20:
            return
        
        # 1. 패턴 탐지
        await self._detect_patterns()
        
        # 2. 진입 신호 체크
        await self._check_entry_signal(candle)
    
    async def _detect_patterns(self):
        """OB, FVG 탐지"""
        candles = list(self.state.candles)
        
        # Order Block 탐지
        ob = self._detect_order_block(candles)
        if ob:
            self.state.add_order_block(ob)
            await self.event_bus.publish(Event(
                type=EventType.ORDER_BLOCK_DETECTED,
                data={'order_block': ob}
            ))
        
        # FVG 탐지
        fvg = self._detect_fvg(candles)
        if fvg:
            self.state.add_fvg(fvg)
            await self.event_bus.publish(Event(
                type=EventType.FVG_DETECTED,
                data={'fvg': fvg}
            ))
    
    def _detect_order_block(self, candles: list) -> Optional[OrderBlock]:
        """Order Block 탐지 로직"""
        if len(candles) < 5:
            return None
        
        recent = candles[-5:]
        last = recent[-1]
        prev = recent[-2]
        
        # 강한 캔들 (몸통이 전체의 70% 이상)
        body = abs(last['close'] - last['open'])
        total = last['high'] - last['low']
        
        if total > 0 and body / total > 0.7:
            if last['close'] > last['open']:  # 양봉
                if prev['close'] < prev['open']:  # 이전 음봉
                    return OrderBlock(
                        type='bullish',
                        top=prev['high'],
                        bottom=prev['low'],
                        timestamp=prev['timestamp']
                    )
            else:  # 음봉
                if prev['close'] > prev['open']:  # 이전 양봉
                    return OrderBlock(
                        type='bearish',
                        top=prev['high'],
                        bottom=prev['low'],
                        timestamp=prev['timestamp']
                    )
        
        return None
    
    def _detect_fvg(self, candles: list) -> Optional[FVG]:
        """FVG 탐지 로직"""
        if len(candles) < 3:
            return None
        
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # Bullish FVG: c1.high < c3.low
        if c1['high'] < c3['low']:
            return FVG(
                type='bullish',
                top=c3['low'],
                bottom=c1['high'],
                timestamp=c2['timestamp']
            )
        
        # Bearish FVG: c1.low > c3.high
        if c1['low'] > c3['high']:
            return FVG(
                type='bearish',
                top=c1['low'],
                bottom=c3['high'],
                timestamp=c2['timestamp']
            )
        
        return None
    
    async def _check_entry_signal(self, candle: dict):
        """진입 신호 체크"""
        if self.state.current_position:
            return
        
        current_price = candle['close']
        
        # Bullish 진입: 가격이 Bullish OB 영역에 진입
        for ob in self.state.get_valid_order_blocks('bullish'):
            if ob.bottom <= current_price <= ob.top:
                has_fvg = any(
                    fvg.bottom <= current_price <= fvg.top
                    for fvg in self.state.get_valid_fvgs('bullish')
                )
                
                await self.event_bus.publish(Event(
                    type=EventType.ENTRY_SIGNAL,
                    data={
                        'side': 'long',
                        'price': current_price,
                        'order_block': ob,
                        'has_fvg_confluence': has_fvg,
                        'stop_loss': ob.bottom * 0.998,
                        'take_profit': current_price * 1.01,
                    }
                ))
                return
        
        # Bearish 진입
        for ob in self.state.get_valid_order_blocks('bearish'):
            if ob.bottom <= current_price <= ob.top:
                has_fvg = any(
                    fvg.bottom <= current_price <= fvg.top
                    for fvg in self.state.get_valid_fvgs('bearish')
                )
                
                await self.event_bus.publish(Event(
                    type=EventType.ENTRY_SIGNAL,
                    data={
                        'side': 'short',
                        'price': current_price,
                        'order_block': ob,
                        'has_fvg_confluence': has_fvg,
                        'stop_loss': ob.top * 1.002,
                        'take_profit': current_price * 0.99,
                    }
                ))
                return
```

### 3.5 Order Manager

```python
# src/execution/order_manager.py

class OrderManager:
    def __init__(
        self, 
        event_bus: EventBus, 
        state: StateStore,
        risk_manager: 'RiskManager',
        client: AsyncClient
    ):
        self.event_bus = event_bus
        self.state = state
        self.risk = risk_manager
        self.client = client
        
        self.event_bus.subscribe(EventType.ENTRY_SIGNAL, self.on_entry_signal)
    
    async def on_entry_signal(self, event: Event):
        """진입 신호 처리"""
        signal = event.data
        
        if not self.risk.can_trade():
            logger.warning("Risk limit reached, skipping trade")
            return
        
        position_size = self.risk.calculate_position_size(
            entry_price=signal['price'],
            stop_loss=signal['stop_loss']
        )
        
        if position_size <= 0:
            return
        
        try:
            side = 'BUY' if signal['side'] == 'long' else 'SELL'
            
            order = await self.client.futures_create_order(
                symbol=settings.symbol,
                side=side,
                type='MARKET',
                quantity=position_size
            )
            
            logger.info(f"Order placed: {order}")
            
            await self._set_stop_loss_take_profit(
                signal['side'],
                position_size,
                signal['stop_loss'],
                signal['take_profit']
            )
            
            self.state.current_position = Position(
                symbol=settings.symbol,
                side=signal['side'],
                entry_price=float(order['avgPrice']),
                size=position_size,
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                timestamp=order['transactTime']
            )
            
            await self.event_bus.publish(Event(
                type=EventType.ORDER_FILLED,
                data={'order': order, 'position': self.state.current_position}
            ))
            
        except Exception as e:
            logger.error(f"Order failed: {e}")
            await self.event_bus.publish(Event(
                type=EventType.ERROR,
                data={'error': str(e), 'context': 'order_execution'}
            ))
    
    async def _set_stop_loss_take_profit(
        self, side: str, quantity: float, stop_loss: float, take_profit: float
    ):
        """SL/TP 주문 설정"""
        close_side = 'SELL' if side == 'long' else 'BUY'
        
        await self.client.futures_create_order(
            symbol=settings.symbol,
            side=close_side,
            type='STOP_MARKET',
            stopPrice=round(stop_loss, 2),
            quantity=quantity,
            reduceOnly=True
        )
        
        await self.client.futures_create_order(
            symbol=settings.symbol,
            side=close_side,
            type='TAKE_PROFIT_MARKET',
            stopPrice=round(take_profit, 2),
            quantity=quantity,
            reduceOnly=True
        )
```

### 3.6 Risk Manager

```python
# src/execution/risk_manager.py

class RiskManager:
    def __init__(self, config: dict, client: AsyncClient):
        self.config = config
        self.client = client
        self.daily_loss = 0.0
        self.trade_count = 0
    
    async def get_account_balance(self) -> float:
        """계좌 잔고 조회"""
        account = await self.client.futures_account_balance()
        for asset in account:
            if asset['asset'] == 'USDT':
                return float(asset['balance'])
        return 0.0
    
    def can_trade(self) -> bool:
        """거래 가능 여부"""
        if self.daily_loss >= self.config['max_daily_loss_percent']:
            return False
        if self.trade_count >= self.config.get('max_daily_trades', 10):
            return False
        return True
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """포지션 크기 계산"""
        balance = asyncio.get_event_loop().run_until_complete(
            self.get_account_balance()
        )
        
        risk_amount = balance * (self.config['risk_per_trade_percent'] / 100)
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            return 0
        
        position_size = risk_amount / price_risk
        max_size = balance * (self.config['max_position_percent'] / 100) / entry_price
        position_size = min(position_size, max_size)
        
        return round(position_size, 3)
    
    def record_trade_result(self, pnl: float):
        self.daily_loss += min(0, pnl)
        self.trade_count += 1
    
    def reset_daily(self):
        self.daily_loss = 0.0
        self.trade_count = 0
```

### 3.7 Discord Notifier

```python
# src/notification/discord.py

import aiohttp

class DiscordNotifier:
    def __init__(self, event_bus: EventBus, webhook_url: str):
        self.event_bus = event_bus
        self.webhook_url = webhook_url
        
        self.event_bus.subscribe(EventType.ORDER_FILLED, self.on_order_filled)
        self.event_bus.subscribe(EventType.POSITION_CLOSED, self.on_position_closed)
        self.event_bus.subscribe(EventType.ERROR, self.on_error)
    
    async def send(self, content: str, embed: dict = None):
        payload = {"content": content}
        if embed:
            payload["embeds"] = [embed]
        
        async with aiohttp.ClientSession() as session:
            await session.post(self.webhook_url, json=payload)
    
    async def on_order_filled(self, event: Event):
        pos = event.data['position']
        embed = {
            "title": f"🟢 포지션 오픈: {pos.side.upper()}",
            "color": 0x00ff00 if pos.side == 'long' else 0xff0000,
            "fields": [
                {"name": "심볼", "value": pos.symbol, "inline": True},
                {"name": "진입가", "value": f"${pos.entry_price:,.2f}", "inline": True},
                {"name": "수량", "value": f"{pos.size}", "inline": True},
                {"name": "SL", "value": f"${pos.stop_loss:,.2f}", "inline": True},
                {"name": "TP", "value": f"${pos.take_profit:,.2f}", "inline": True},
            ]
        }
        await self.send("", embed)
    
    async def on_position_closed(self, event: Event):
        pnl = event.data['pnl']
        emoji = "🟢" if pnl >= 0 else "🔴"
        embed = {
            "title": f"{emoji} 포지션 종료",
            "color": 0x00ff00 if pnl >= 0 else 0xff0000,
            "fields": [
                {"name": "PnL", "value": f"${pnl:,.2f}", "inline": True},
                {"name": "종료 사유", "value": event.data.get('reason', 'Unknown'), "inline": True},
            ]
        }
        await self.send("", embed)
    
    async def on_error(self, event: Event):
        await self.send(f"⚠️ **Error**: {event.data['error']}")
```

---

## 4. 디렉토리 구조 (MVP)

```
ict-auto-trader/
├── src/
│   ├── __init__.py
│   ├── main.py                 # 진입점
│   ├── config.py               # 설정 로드
│   ├── core/
│   │   ├── __init__.py
│   │   ├── event_bus.py        # 단순 이벤트 버스
│   │   └── state_store.py      # 상태 저장소
│   ├── data/
│   │   ├── __init__.py
│   │   └── websocket_client.py # 바이낸스 웹소켓
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── patterns.py         # OB, FVG 탐지 함수
│   │   └── signal_engine.py    # 신호 생성
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── order_manager.py    # 주문 관리
│   │   └── risk_manager.py     # 리스크 관리
│   └── notification/
│       ├── __init__.py
│       └── discord.py          # Discord 알림
├── config.yaml                 # 설정 파일
├── .env                        # API 키 등
├── requirements.txt
└── README.md
```

---

## 5. 설정 파일

### 5.1 .env (비밀 정보)

```bash
# Binance Testnet API
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/yyy
```

### 5.2 config.yaml (트레이딩 설정)

```yaml
# config.yaml

trading:
  symbol: "BTCUSDT"
  interval: "15m"
  use_testnet: true

strategy:
  order_block:
    min_body_ratio: 0.7
    max_touches: 3
    max_age_candles: 100
  
  fvg:
    min_gap_percent: 0.1
    max_age_candles: 50

risk:
  risk_per_trade_percent: 1.0
  max_daily_loss_percent: 3.0
  max_position_percent: 10.0
  max_daily_trades: 5
  default_rr_ratio: 2.0

logging:
  level: INFO
  file: logs/trader.log
```

---

## 6. 메인 실행 코드

```python
# src/main.py

import asyncio
import os
import yaml
from dotenv import load_dotenv
from loguru import logger

from binance import AsyncClient

from core.event_bus import EventBus
from core.state_store import StateStore
from data.websocket_client import BinanceWebSocket
from strategy.signal_engine import SignalEngine
from execution.order_manager import OrderManager
from execution.risk_manager import RiskManager
from notification.discord import DiscordNotifier

load_dotenv()

async def main():
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    event_bus = EventBus()
    state = StateStore()
    
    client = await AsyncClient.create(
        api_key=os.getenv('BINANCE_API_KEY'),
        api_secret=os.getenv('BINANCE_API_SECRET'),
        testnet=config['trading']['use_testnet']
    )
    
    risk_manager = RiskManager(config['risk'], client)
    
    ws_client = BinanceWebSocket(
        event_bus=event_bus,
        symbol=config['trading']['symbol'],
        interval=config['trading']['interval']
    )
    
    signal_engine = SignalEngine(event_bus, state, config['strategy'])
    order_manager = OrderManager(event_bus, state, risk_manager, client)
    discord = DiscordNotifier(event_bus, os.getenv('DISCORD_WEBHOOK_URL'))
    
    logger.info("Starting ICT Auto Trader MVP...")
    logger.info(f"Symbol: {config['trading']['symbol']}")
    logger.info(f"Interval: {config['trading']['interval']}")
    logger.info(f"Testnet: {config['trading']['use_testnet']}")
    
    await ws_client.connect()
    
    await asyncio.gather(
        event_bus.start(),
        ws_client.start_kline_stream()
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. 확장 로드맵

### 전체 로드맵 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ICT Auto Trader 확장 로드맵                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 0        Phase 1        Phase 2        Phase 3        Phase 4       │
│  (MVP)          (전략강화)      (안정성)       (Liquidity)    (GUI)         │
│  3-4주          +2주           +2주           +1주           +2주          │
│                                                                             │
│  ┌─────┐       ┌─────┐       ┌─────┐       ┌─────┐       ┌─────┐          │
│  │OB   │       │Market│       │Bounded│     │Equal │       │React│          │
│  │FVG  │──────▶│Struct│──────▶│Queue │──────▶│Highs │──────▶│Dash │         │
│  │     │       │MTF   │       │Worker│       │Sweep │       │board│          │
│  └─────┘       └─────┘       └─────┘       └─────┘       └─────┘          │
│                                                                             │
│  ───────────────────────────────────────────────────────────────────────▶  │
│  Testnet                                               Mainnet              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 0: MVP (현재) - 3-4주

**상태**: 🚧 진행 중

```
✅ 이벤트 기반 구조 (단순 EventBus)
✅ Order Block 탐지
✅ FVG 탐지
✅ Testnet 주문 실행
✅ 기본 리스크 관리
✅ Discord 알림
✅ 단일 타임프레임 (15m)
```

**완료 기준**:
- [ ] Testnet에서 주문 실행 성공
- [ ] 24시간 연속 운영 안정
- [ ] Discord 알림 동작

---

### Phase 1: 전략 강화 - 2주

**목표**: 신호 품질 개선

```yaml
추가 기능:
  - Market Structure 분석 (BOS/CHoCH)
  - 스윙 포인트 탐지 (HH, HL, LH, LL)
  - 다중 타임프레임 (15m + 1h 또는 4h)
  - OTE Zone 계산
  - Confluence 점수 시스템

신규 파일:
  - src/strategy/market_structure.py
  - src/strategy/ote.py

수정 파일:
  - src/core/state_store.py (스윙 포인트 추가)
  - src/strategy/signal_engine.py (Confluence 로직)
  - config.yaml (MTF 설정)
```

**이벤트 추가**:
```python
class EventType(Enum):
    # 기존...
    
    # Phase 1 추가
    SWING_POINT_FORMED = "swing_point_formed"
    BOS_DETECTED = "bos_detected"
    CHOCH_DETECTED = "choch_detected"
```

**Confluence 점수 예시**:
```python
WEIGHTS = {
    'market_structure_aligned': 2.0,  # 상위 TF 추세 일치
    'order_block': 2.0,
    'fvg': 1.5,
    'ote_zone': 1.5,
}
ENTRY_THRESHOLD = 4.0
```

**트리거 조건**: MVP 동작 확인 후, 신호 품질 개선 필요 느낄 때

---

### Phase 2: 안정성 강화 - 2주

**목표**: 이벤트 병목 방지

```yaml
추가 기능:
  - Bounded Queue 적용
  - 워커 분리 (데이터 / 분석 / 주문)
  - 오버플로우 정책 (DROP_OLDEST, DROP_NEWEST)
  - 큐 헬스 모니터링
  - 타임아웃 처리
  - 재연결 로직 강화

신규 파일:
  - src/core/bounded_queue.py
  - src/core/worker_pool.py (선택)

수정 파일:
  - src/core/event_bus.py (대폭 수정)
```

**아키텍처 변경**:
```
Before (MVP):
  WebSocket → [단일 Queue] → 모든 처리

After (Phase 2):
  WebSocket → [Raw Queue] → Data Worker
                              ↓
                         [Analysis Queue] → Signal Worker
                              ↓
                         [Order Queue] → Order Worker
```

**트리거 조건**:
- 다중 타임프레임 처리 시 지연 발생
- 큐 백로그 쌓임 관찰
- 메시지 유실 의심

---

### Phase 3: Liquidity Sweep - 1주

**목표**: 추가 전략 요소

```yaml
추가 기능:
  - Equal Highs/Lows 탐지
  - Liquidity Pool 식별
  - Sweep 패턴 인식
  - Sweep 후 반전 진입

신규 파일:
  - src/strategy/liquidity.py

수정 파일:
  - src/core/state_store.py
  - src/strategy/signal_engine.py
```

**이벤트 추가**:
```python
class EventType(Enum):
    # 기존...
    EQUAL_HIGHS_DETECTED = "equal_highs_detected"
    EQUAL_LOWS_DETECTED = "equal_lows_detected"
    LIQUIDITY_SWEPT = "liquidity_swept"
```

**트리거 조건**: OB + FVG만으로 신호 부족 시

---

### Phase 4: GUI 대시보드 - 2주

**목표**: 모니터링 및 설정 관리

```yaml
추가 기능:
  - React 대시보드
  - 실시간 포지션 모니터링
  - 이벤트 큐 상태 시각화
  - 설정 GUI 변경 (슬라이더)
  - 패턴 시각화 (선택)

신규 폴더:
  - src/api/ (FastAPI)
  - frontend/ (React + Vite + Tailwind)

설정 분리:
  - .env (고정: API 키)
  - trading_config.yaml (동적: 전략 파라미터)
```

**트리거 조건**:
- 설정 변경 빈번
- 터미널 모니터링 불편
- Phase 1~3 완료 후

---

### Phase 5: Mainnet + 최적화 - 지속

```yaml
작업:
  - Testnet 충분히 검증 후 Mainnet 전환
  - 파라미터 튜닝 (실거래 데이터 기반)
  - 다중 심볼 지원 (선택)
  - 백테스팅 엔진 (선택)
  - 성과 분석 리포트
```

---

## 8. 확장 결정 기준 요약

| Phase | 트리거 조건 | 예상 시점 |
|-------|-------------|-----------|
| **Phase 1** | MVP 안정 + 신호 품질 불만족 | MVP 완료 후 1-2주 |
| **Phase 2** | 이벤트 지연/유실 발생 | MTF 도입 후 |
| **Phase 3** | OB+FVG 신호 부족 | Phase 1 이후 |
| **Phase 4** | 설정 변경 빈번 + 모니터링 필요 | Phase 1~3 이후 |
| **Phase 5** | Testnet 2주 안정 운영 | Phase 1~4 완료 후 |

---

## 9. MVP 개발 체크리스트

### Week 1: 기반 구축
- [ ] 프로젝트 구조 생성
- [ ] .env, config.yaml 설정
- [ ] EventBus 구현
- [ ] StateStore 구현
- [ ] BinanceWebSocket 연결
- [ ] 캔들 수신 테스트 (로그 출력)

### Week 2: 전략 구현
- [ ] Order Block 탐지 로직
- [ ] FVG 탐지 로직
- [ ] SignalEngine 통합
- [ ] 신호 발생 테스트 (로그 확인)

### Week 3: 실행 구현
- [ ] RiskManager 구현
- [ ] OrderManager 구현
- [ ] Testnet 주문 테스트
- [ ] SL/TP 설정 테스트

### Week 4: 마무리
- [ ] Discord 알림 연동
- [ ] 에러 핸들링 추가
- [ ] 로깅 정리
- [ ] 24시간 운영 테스트
- [ ] 버그 수정

---

## 10. requirements.txt

```
python-binance>=1.0.19
python-dotenv>=1.0.0
pyyaml>=6.0
aiohttp>=3.9.0
loguru>=0.7.0
pydantic>=2.0.0
```

---

## 11. 빠른 시작

```bash
# 1. 클론 및 설정
git clone https://github.com/your-repo/ict-auto-trader.git
cd ict-auto-trader
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 환경 설정
cp .env.example .env
# .env 편집: API 키, Webhook URL

# 3. 설정 확인
# config.yaml: use_testnet: true

# 4. 실행
python -m src.main
```

---

*MVP PRD 끝*
