##### README ######################################################################

# [ LONG 조건 ]
# 1. 전 봉이 양봉.
# 2. 전전 봉이 음봉.
# 3. 전전 봉의 RSI가 RSI_OVERSOLD 아래.
# 4. 전 봉, 전전 봉 중 최저가 < 그 전 28개 봉 중 최저가
# 5. 전전 봉의 RSI > 그 전 28개의 RSI 값중 최저 값
#
# [ SHORT 조건 ]
# 1. 전 봉이 음봉.
# 2. 전전 봉이 양봉.
# 3. 전전 봉의 RSI가 RSI_OVERBOUGHT 위.
# 4. 전 봉, 전전 봉 중 최고가 > 그 전 28개 봉 중 최고가
# 5. 전전 봉의 RSI < 그 전 28개의 RSI 값중 최고 값
#
# 익절 : +2% (레듀스 온리 설정)
# 손절 : -1% (스탑 로스 설정)
# 손절 변경점 : +0.5%
# 변경된 손절 : 0.0%( 본절 로스 설정)
#
# 전략 : RSI 다이버전스를 통한 매매로 봉이 바뀌는 순간 거래하는 방식이다.
#
# 매 체결 시 네이버 메일로 보내기.
# 예외가 발생했을 시 로그 남기기(메일은 보낼 수 없다. 만약 네트워크 오류라면 예외 처리를 하는 도중에 예외가 발생해 프로그램이 종료될 것이다.)

##### 모듈 import ##################################################################

import datetime
import math
import smtplib
from email.mime.text import MIMEText
import ccxt
import numpy
import talib
import time


##### 프로그램 상수 ##################################################################


API_KEY = 'MY_API_KEY'
SECRET_KEY = 'MY_SECRET_KEY'

SEND_EMAIL_ADDRESS = 'MYMAIL1@naver.com'  # 전송 메일 네이버 주소
SEND_EMAIL_PASSWORD = 'PASSWORD'  # 전송 메일 비밀번호
RECEIVE_EMAIL_ADDRESS = 'MYMAIL2@naver.com'  # 수신 메일 네이버 주소
SMTP_NAME = 'smtp.naver.com'
SMTP_PORT = 587

SYMBOL = 'BTC'  # 거래 코인
SYMBOL_PAIR = 'USDT'  # 구매 코인
LEVERAGE = 10  # 레버리지
TIME_FRAME = 15  # 분봉 기준
TRADE_QUANTITY_RATIO = 95  # 전체 잔고의 몇퍼센트를 거래에 사용할지

RSI_PERIOD = 14  # RSI 기준 봉 개수
RSI_OVERBOUGHT = 65  # 과매수 RSI
RSI_OVERSOLD = 35  # 과매도 RSI

STOP_LOSS_PERCENT = 1  # 스탑로스 퍼센트(레버리지 미포함) => 실제 손절 퍼센트는 (STOP_LOSS_PERCENT * LEVERAGE %) 이다.
REDUCE_ONLY_PERCENT = 2  # 익절 퍼센트(레버리지 미포함)
CHANGED_STOP_LOSS_PERCENT = 0  # 변경된 스탑로스 퍼센트(레버리지 미포함) => 어느정도 이득을 본 상태에서는 손절가를 줄여서 본절 청산이 나도록 하는 것이다.
CHANGE_SPOT_PERCENT = 0.5  # STOP_LOSS_CHANGED 값을 변경할 시점에 해당하는 퍼센트(레버리지 미포함) => 이 지점에 닿으면 바로 위의 변수로 손절가를 변경하는 것이다.


##### 함수 ##########################################################################


# 바이낸스 선물 객체 생성
def get_Binance():
    local_binance = ccxt.binance(config={
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'enableRateLimit': True,  # API 요청 비율 조절 => 거래소의 API 사용 금지 방어
        'options': {
            'defaultType': 'future',  # 선물 객체 설정
        },
    })

    return local_binance


# 레버리지 설정
def config_Leverage():
    global binance

    binance.fapiPrivate_post_leverage({
        'symbol': SYMBOL + SYMBOL_PAIR,
        'leverage': LEVERAGE,
    })


# 거래 코인 현재가 조회
def get_Now_Price():
    return binance.fetch_ticker(SYMBOL + '/' + SYMBOL_PAIR)['close']


# 내 주문 평단가 계산
def get_My_Order_Price():
    myPosition = None
    positions = binance.fetch_positions()
    for position in positions:
        if position['symbol'] == SYMBOL + SYMBOL_PAIR:
            myPosition = position

    my_entry_price = float(myPosition['entryPrice'])

    # 잔고를 정확히 해야한다. 정밀도가 필요한 값에서 그냥 내보내면 반올림 되서 실제보다 많게 잔고가 표기되어 다음과 같은 에러가 발생할 수 있다.
    # ccxt.base.errors.InsufficientFunds: binance {"code":-2019,"msg":"Margin is insufficient."}
    # 따라서 내림으로 처리를 해줘야 한다.
    my_entry_price = math.floor(my_entry_price * 1000) / 1000

    return my_entry_price


# 내 잔고 구하기
def get_My_Balance():
    my_balance = binance.fetch_balance()[SYMBOL_PAIR]['total']

    # 잔고를 정확히 해야한다. 정밀도가 필요한 값에서 그냥 내보내면 반올림 되서 실제보다 많게 잔고가 표기되어 다음과 같은 에러가 발생할 수 있다.
    # ccxt.base.errors.InsufficientFunds: binance {"code":-2019,"msg":"Margin is insufficient."}
    # 따라서 내림으로 처리를 해줘야 한다.
    my_balance = math.floor(my_balance * 1000) / 1000

    return my_balance


# TIME_FRAME 분봉 ohlcv 조회 (시간, 시가, 고가, 저가, 종가, 거래량)
def get_Ohlcv():
    return binance.fetch_ohlcv(SYMBOL + '/' + SYMBOL_PAIR, timeframe=str(TIME_FRAME) + 'm')


# RSI 구하기 (RSI_PERIOD 개 기준).
# 시간이 바뀌는 시점에 get_Ohlcv()를 호출하게 되면, 다른 리스트를 가질 수 있기 때문에 하나의 ohlcv로 사용하는 것을 보장하기 위해 외부에서 ohlcv를 받아오는 방식을 택했다.
def get_RSI(ohlcvs):
    # 종가만 추출
    close_set = []
    for ohlcv in ohlcvs:
        close_set.append(ohlcv[4])

    # talib에서 사용할 수 있게 ndarray로 변환
    close_set = numpy.array(close_set)

    # RSI 전체 추출
    RSIs = talib.RSI(close_set, RSI_PERIOD)

    return RSIs


# 거래할 코인 개수(레버리지 적용한 개수)
def get_Trade_Quantity():
    # 거래 가능한 코인의 TRADE_QUANTITY_RATIO % 투자.
    trade_quantity = get_My_Balance() * LEVERAGE / get_Now_Price() * TRADE_QUANTITY_RATIO / 100

    # 잔고를 정확히 해야한다. 정밀도가 필요한 값에서 그냥 내보내면 반올림 되서 실제보다 많게 잔고가 표기되어 다음과 같은 에러가 발생할 수 있다.
    # ccxt.base.errors.InsufficientFunds: binance {"code":-2019,"msg":"Margin is insufficient."}
    # 따라서 내림으로 처리를 해줘야 한다.
    trade_quantity = math.floor(trade_quantity * 1000) / 1000

    return trade_quantity


# 포지션이 있을 때 처리하는 프로세스
def fill_Position_Process():
    now_price = get_Now_Price()
    ordered_price = get_My_Order_Price()

    # 포지션이 LONG 이면
    if POSITION_SIDE == 'LONG':
        in_Long_Position_Process(now_price, ordered_price)

    # 포지션이 SHORT 이면
    else:
        in_Short_Position_Process(now_price, ordered_price)


# 롱 포지션에 있을 때 처리하는 프로세스
def in_Long_Position_Process(now_price, ordered_price):
    global IN_POSITION, STOP_LOSS_CHANGED

    # 익절 조건 진입 시 매도
    if now_price > ordered_price * (1 + REDUCE_ONLY_PERCENT / 100):
        # 레듀스 온리로 시장가 매도 주문
        make_Reduce_Only_Order('sell')
        IN_POSITION = False
        STOP_LOSS_CHANGED = False

        # 레듀스 온리 체결 메시지 보내기
        send_Message('Long 포지션을 REDUCE ONLY 체결 완료')

    # STOP_LOSS 변경 ( CHANGE_SPOT_PERCENT % 이상 이득 시, 손절 라인을 CHANGED_STOP_LOSS_PERCENT % 이득인 지점으로 바꾼다.)
    if (not STOP_LOSS_CHANGED) and (now_price > ordered_price * (1 + CHANGE_SPOT_PERCENT / 100)):
        STOP_LOSS_CHANGED = True

    # STOP_LOSS 지점 도달 시 손절
    if STOP_LOSS_CHANGED:
        if now_price < ordered_price * (1 - CHANGED_STOP_LOSS_PERCENT / 100):
            # 레듀스 온리로 시장가 매도 주문
            make_Reduce_Only_Order('sell')
            IN_POSITION = False
            STOP_LOSS_CHANGED = False

            # 스탑로스 체결 메시지 보내기
            send_Message('Long 포지션을 본절 STOP LOSS 체결 완료')
    else:
        if now_price < ordered_price * (1 - STOP_LOSS_PERCENT / 100):
            # 레듀스 온리로 시장가 매도 주문
            make_Reduce_Only_Order('sell')
            IN_POSITION = False
            STOP_LOSS_CHANGED = False

            # 스탑로스 체결 메시지 보내기
            send_Message('Long 포지션을 STOP LOSS 체결 완료')


# 숏 포지션에 있을 때 처리하는 프로세스
def in_Short_Position_Process(now_price, ordered_price):
    global IN_POSITION, STOP_LOSS_CHANGED

    # 익절 조건 진입 시 매수
    if now_price < ordered_price * (1 - REDUCE_ONLY_PERCENT / 100):
        # 레듀스 온리로 시장가 매수 주문
        make_Reduce_Only_Order('buy')
        IN_POSITION = False
        STOP_LOSS_CHANGED = False

        # 레듀스 온리 체결 메시지 보내기
        send_Message('숏 포지션을 REDUCE ONLY 체결 완료')

    # STOP_LOSS 변경 ( CHANGE_SPOT_PERCENT % 이상 이득 시, 손절 라인을 CHANGED_STOP_LOSS_PERCENT % 이득인 지점으로 바꾼다.)
    if (not STOP_LOSS_CHANGED) and (now_price < ordered_price * (1 - CHANGE_SPOT_PERCENT / 100)):
        STOP_LOSS_CHANGED = True

    # STOP_LOSS 지점 도달 시 손절
    if STOP_LOSS_CHANGED:
        if now_price > ordered_price * (1 + CHANGED_STOP_LOSS_PERCENT / 100):
            # 레듀스 온리로 시장가 매수 주문
            make_Reduce_Only_Order('buy')
            IN_POSITION = False
            STOP_LOSS_CHANGED = False

            # 스탑로스 체결 메시지 보내기
            send_Message('숏 포지션을 본절 STOP LOSS 체결 완료')

    else:
        if now_price > ordered_price * (1 + STOP_LOSS_PERCENT / 100):
            # 레듀스 온리로 시장가 매수 주문
            make_Reduce_Only_Order('buy')
            IN_POSITION = False
            STOP_LOSS_CHANGED = False

            # 스탑로스 체결 메시지 보내기
            send_Message('숏 포지션을 STOP LOSS 체결 완료')


# 레듀스 온리 주문 ( 롱으로 주문했던 것을 포지션 정리하려면 SIDE = sell 을 넣으면 되고, 숏으로 주문했었다면 포지션 정리하려면 SIDE = buy 를 넣으면 된다.)
def make_Reduce_Only_Order(side):
    binance.create_order(
        symbol=SYMBOL + '/' + SYMBOL_PAIR,
        type='market',
        side=side,
        amount=TRADED_QUANTITY,
        params={
            'type': 'future',
            "reduceOnly": True,
        },
    )

    time.sleep(TIME_FRAME * 60)


# 포지션이 없을 때 처리하는 프로세스
def empty_Position_Process():
    global IN_POSITION, POSITION_SIDE, STOP_LOSS_CHANGED

    ohlcvs = get_Ohlcv()
    RSIs = get_RSI(ohlcvs)

    if is_Long_Condition(RSIs, ohlcvs) == True:
        # 롱 진입
        make_Order('buy')
        IN_POSITION = True
        POSITION_SIDE = 'LONG'
        STOP_LOSS_CHANGED = False

        # 체결 메시지 보내기
        send_Message("LONG 포지션 체결")

    elif is_Short_Condition(RSIs, ohlcvs) == True:
        # 숏 진입
        make_Order('sell')
        IN_POSITION = True
        POSITION_SIDE = 'SHORT'
        STOP_LOSS_CHANGED = False

        # 체결 메시지 보내기
        send_Message("SHORT 포지션 체결")


def is_Long_Condition(RSIs, ohlcvs):
    # 전 봉이 양봉 => 음봉이면 false
    if ohlcvs[-2][1] > ohlcvs[-2][4]:
        return False

    # 전전 봉이 음봉 => 양봉이면 false
    if ohlcvs[-3][1] < ohlcvs[-3][4]:
        return False

    # 전전 봉의 RSI가 RSI_OVERSOLD 아래 => RSI_OVERSOLD 위이면 false
    if RSIs[-3] > RSI_OVERSOLD:
        return False

    # 저가만 추출
    low_set = []
    for ohlcv in ohlcvs:
        low_set.append(ohlcv[3])

    # 전 봉, 전전 봉 중 최저가
    min_value_main = min(low_set[-3:-1])

    # 나머지 28개 봉 중 최저가
    min_value_others = min(low_set[-31:-3])

    # 전 봉, 전전 봉 중 최저가 < 나머지 28개 봉 중 최저가 => 전 봉, 전전 봉 중 최저가 > 나머지 28개 봉 중 최저가  이면 false
    if min_value_main > min_value_others:
        return False

    # 전전전 봉부터 그 전 28개의 RSI 값 중 최저값
    min_rsi_other = min(RSIs[-31:-3])

    # 전전 봉의 RSI > 그 전 28개의 RSI 값중 최저 값 => 전전 봉의 RSI < 그 전 28개의 RSI 값중 최저 값  이면 false
    if RSIs[-3] < min_rsi_other:
        return False

    return True


def is_Short_Condition(RSIs, ohlcvs):
    # 전 봉이 음봉 => 양봉이면 false
    if ohlcvs[-2][1] < ohlcvs[-2][4]:
        return False

    # 전전 봉이 양봉 => 음봉이면 false
    if ohlcvs[-3][1] > ohlcvs[-3][4]:
        return False

    # 전전 봉의 RSI가 RSI가 RSI_OVERBOUGHT 위 => RSI_OVERBOUGHT 아래이면 false
    if RSIs[-3] < RSI_OVERBOUGHT:
        return False

    # 고가만 추출
    high_set = []
    for ohlcv in ohlcvs:
        high_set.append(ohlcv[2])

    # 전 봉, 전전 봉 중 최고가
    max_value_main = max(high_set[-3:-1])

    # 나머지 28개 봉 중 최고가
    max_value_others = max(high_set[-31:-3])

    # 전 봉, 전전 봉 중 최고가 > 그 전 28개 봉 중 최고가 => 전 봉, 전전 봉 중 최고가 < 그 전 28개 봉 중 최고가  이면 false
    if max_value_main < max_value_others:
        return False

    # 전전전 봉부터 그 전 28개의 RSI 값 중 최고값
    max_rsi_other = max(RSIs[-31:-3])

    # 전전 봉의 RSI < 그 전 28개의 RSI 값중 최고 값 => 전전 봉의 RSI > 그 전 28개의 RSI 값중 최고 값  이면 false
    if RSIs[-3] > max_rsi_other:
        return False

    return True


# 주문
def make_Order(side):
    global TRADED_QUANTITY

    TRADED_QUANTITY = get_Trade_Quantity()

    binance.create_order(
        symbol=SYMBOL + '/' + SYMBOL_PAIR,
        type='market',
        side=side,
        amount=TRADED_QUANTITY,
        params={
            'type': 'future',
        },
    )


# 메시지 보내기
def send_Message(text):
    message = MIMEText('.')

    message['Subject'] = text
    message['From'] = SEND_EMAIL_ADDRESS
    message['To'] = RECEIVE_EMAIL_ADDRESS

    smtp = smtplib.SMTP(SMTP_NAME, SMTP_PORT)  # 메일 서버 연결
    smtp.starttls()  # TLS 보안 처리
    smtp.login(SEND_EMAIL_ADDRESS, SEND_EMAIL_PASSWORD)  # 로그인
    smtp.sendmail(SEND_EMAIL_ADDRESS, RECEIVE_EMAIL_ADDRESS, message.as_string())  # 메일 전송, 문자열로 변환하여 보냄.
    smtp.close()  # smtp 서버 연결종료.


##### 메인 로직 ######################################################################


binance = get_Binance()  # binance 선물 객체 생성

# ccxt.base.errors.InvalidNonce: binance {"code":-1021,"msg":"Timestamp for this request was 1000ms ahead of the server's time."}
# 위 에러 발생시 서버와 시간을 동기화시키기 위해 아래의 코드 실행. 아래의 숫자 조절 가능
# binance.nonce = lambda: binance.milliseconds() - 1000

config_Leverage()  # 레버리지 설정

IN_POSITION = False  # 현재 포지션이 존재하는지
POSITION_SIDE = ''  # 포지션 방향. LONG or SHORT
TRADED_QUANTITY = 0  # 매수했던 코인량( 매도 시점에 필요). 거래 하기 전이기 때문에 초기값을 0으로 설정했다.
STOP_LOSS_CHANGED = False  # 스탑로스 값 변경 여부

send_Message("프로그램 가동 시작")

while True:
    try:
        # 포지션이 있을 때
        if IN_POSITION:
            fill_Position_Process()

        # 포지션이 없을 때
        else:
            empty_Position_Process()

    except Exception as e:
        print(str(datetime.datetime.now()) + " : 예외 발생")  # 문자를 보낼 수는 없다. 네트워크 에러라면 문자를 보내는 것도 에러를 발생시킨다.
        print(e)

    finally:
        # 잦은 api 요청 방지
        time.sleep(3)

