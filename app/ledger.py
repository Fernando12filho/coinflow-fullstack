"""Portfolio calculation engine.

Pure Python with no Flask imports. Every amount is a ``decimal.Decimal``.

Definitions used throughout CoinFlow:

- **Break-even price**: (invested - proceeds) / BTC held. Selling everything at this
  price leaves you exactly even overall. It goes negative once sales have returned
  more than you put in.
- **Average cost**: cost basis / BTC held, where each sale removes cost at the
  average cost at that moment.
- **Total P&L**: proceeds + current value - invested.
- **Realized P&L**: for each sale, net proceeds minus the average cost of the BTC
  that left. **Unrealized P&L**: current value minus remaining cost basis.
  Realized + unrealized always equals total P&L.

Fees paid in fiat are added to the cost of a buy or taken off the proceeds of a sale.
Fees paid in BTC reduce the BTC you hold.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

BUY = 'buy'
SELL = 'sell'
REWARD = 'reward'
SIDES = (BUY, SELL, REWARD)
BTC = 'BTC'

ZERO = Decimal('0')
HUNDRED = Decimal('100')


class LedgerError(Exception):
    """The trades don't form a valid history (e.g. selling BTC you don't hold)"""


@dataclass(frozen=True)
class Trade:
    """One movement of BTC in or out of the portfolio.

    ``btc`` is the BTC bought, sold or received (before fees). ``fiat`` is what was
    paid for a buy or received for a sale (before fees); it is zero for a reward.
    """
    side: str
    date: datetime
    btc: Decimal
    fiat: Decimal
    fee: Decimal = ZERO
    fee_asset: str | None = None  # BTC or the trade currency; defaults to the currency
    currency: str = 'USD'
    id: int | None = None

    def __post_init__(self):
        if self.fee_asset is None:
            object.__setattr__(self, 'fee_asset', self.currency)
        for name in ('btc', 'fiat', 'fee'):
            if not isinstance(getattr(self, name), Decimal):
                raise TypeError(f'{name} must be a Decimal')

        if self.side not in SIDES:
            raise ValueError(f'Unknown trade side: {self.side!r}')
        if self.btc <= 0:
            raise ValueError('BTC amount must be positive')
        if self.side == REWARD:
            if self.fiat != 0:
                raise ValueError('A reward must have a fiat amount of zero')
        elif self.fiat <= 0:
            raise ValueError('The fiat amount must be positive')
        if self.fee < 0:
            raise ValueError('Fee cannot be negative')
        if self.fee_asset not in (self.currency, BTC):
            raise ValueError(f'Fee must be in {self.currency} or {BTC}')

    @property
    def price(self):
        """Price per BTC on this trade (zero for a reward)"""
        return self.fiat / self.btc

    @property
    def fee_btc(self):
        return self.fee if self.fee_asset == BTC else ZERO

    @property
    def fee_fiat(self):
        return self.fee if self.fee_asset != BTC else ZERO


@dataclass(frozen=True)
class LedgerRow:
    """A trade plus the running position right after it"""
    trade: Trade
    held: Decimal
    break_even: Decimal | None
    average_cost: Decimal | None
    realized_pnl: Decimal | None  # only set on sales


@dataclass(frozen=True)
class Position:
    currency: str | None
    held: Decimal
    invested: Decimal      # everything paid for buys, including fiat fees
    proceeds: Decimal      # everything received from sales, after fiat fees
    fees: Decimal          # all fees valued in fiat (BTC fees at the trade price)
    cost_basis: Decimal    # average-cost basis of the BTC still held
    realized_pnl: Decimal
    break_even: Decimal | None
    average_cost: Decimal | None
    buys: int
    sells: int
    rewards: int


@dataclass(frozen=True)
class Valuation:
    price: Decimal | None
    value: Decimal | None
    total_pnl: Decimal | None
    total_pnl_percent: Decimal | None
    realized_pnl: Decimal
    unrealized_pnl: Decimal | None
    unrealized_pnl_percent: Decimal | None


def run_ledger(trades):
    """Replay trades in date order. Returns (rows, position).

    Trades on the same date keep the order they were given in.
    Raises LedgerError if the history is impossible.
    """
    ordered = sorted(trades, key=lambda t: t.date)
    currencies = {t.currency for t in ordered}
    if len(currencies) > 1:
        raise LedgerError(f'All trades must use the same currency, found: {", ".join(sorted(currencies))}')

    held = invested = proceeds = fees = cost_basis = realized = ZERO
    counts = {BUY: 0, SELL: 0, REWARD: 0}
    rows = []

    for t in ordered:
        counts[t.side] += 1
        fees += t.fee_fiat + t.fee_btc * t.price
        trade_realized = None

        if t.side == SELL:
            btc_out = t.btc + t.fee_btc
            if btc_out > held:
                raise LedgerError(
                    f'Sale on {t.date:%Y-%m-%d} needs {btc_out} BTC but only {held} BTC is held at that point'
                )
            cost_removed = cost_basis * btc_out / held
            net = t.fiat - t.fee_fiat
            proceeds += net
            trade_realized = net - cost_removed
            realized += trade_realized
            held -= btc_out
            cost_basis = cost_basis - cost_removed if held else ZERO
        else:
            btc_in = t.btc - t.fee_btc
            if btc_in <= 0:
                raise LedgerError(f'Fee on {t.date:%Y-%m-%d} is larger than the BTC received')
            held += btc_in
            if t.side == BUY:
                cost = t.fiat + t.fee_fiat
                invested += cost
                cost_basis += cost

        rows.append(LedgerRow(
            trade=t,
            held=held,
            break_even=_break_even(invested, proceeds, held),
            average_cost=cost_basis / held if held else None,
            realized_pnl=trade_realized,
        ))

    position = Position(
        currency=currencies.pop() if currencies else None,
        held=held,
        invested=invested,
        proceeds=proceeds,
        fees=fees,
        cost_basis=cost_basis,
        realized_pnl=realized,
        break_even=_break_even(invested, proceeds, held),
        average_cost=cost_basis / held if held else None,
        buys=counts[BUY],
        sells=counts[SELL],
        rewards=counts[REWARD],
    )
    return rows, position


def valuation(position, price):
    """Value a position at ``price`` (a Decimal, or None when the price is unknown)"""
    if price is None:
        return Valuation(None, None, None, None, position.realized_pnl, None, None)

    value = position.held * price
    total = position.proceeds + value - position.invested
    unrealized = value - position.cost_basis
    return Valuation(
        price=price,
        value=value,
        total_pnl=total,
        total_pnl_percent=total / position.invested * HUNDRED if position.invested else None,
        realized_pnl=position.realized_pnl,
        unrealized_pnl=unrealized,
        unrealized_pnl_percent=unrealized / position.cost_basis * HUNDRED if position.cost_basis else None,
    )


def _break_even(invested, proceeds, held):
    return (invested - proceeds) / held if held else None
