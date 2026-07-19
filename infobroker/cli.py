"""Infobroker interactive CLI — learn, research, paper/live trade."""

from __future__ import annotations

import getpass
from datetime import datetime, timedelta

from infobroker.auth import login, migrate_legacy_users_json, register
from infobroker.brokers import (
    OrderRequest,
    OrderSide,
    OrderType,
    create_broker,
    describe_brokers,
)
from infobroker.brokers.paper import PaperBroker
from infobroker.config import ROOT, get_settings
from infobroker.data import get_fundamentals, get_historical_data, get_stock_quote
from infobroker.education import get_lesson, list_lessons
from infobroker.risk import evaluate_order, teaching_checklist
from infobroker.strategies import run_backtest


def _prompt_trade(broker, user: str) -> None:
    settings = get_settings()
    is_live = settings.broker not in {"paper"} and not (
        settings.broker == "alpaca" and settings.alpaca_paper
    )
    print("\n".join(teaching_checklist("?", "buy")))
    symbol = input("Symbol: ").strip().upper()
    side_raw = input("Side (buy/sell): ").strip().lower()
    side = OrderSide.BUY if side_raw.startswith("b") else OrderSide.SELL
    qty = float(input("Quantity: ").strip())
    stop_raw = input("Stop-loss price (optional, Enter to skip): ").strip()
    stop_price = float(stop_raw) if stop_raw else None
    take_raw = input("Take-profit price (optional): ").strip()
    take_profit = float(take_raw) if take_raw else None

    quote = broker.get_quote(symbol)
    account = broker.get_account()
    positions = broker.list_positions()
    req = OrderRequest(
        symbol=symbol,
        side=side,
        qty=qty,
        order_type=OrderType.MARKET,
        stop_price=stop_price,
    )
    verdict = evaluate_order(
        req,
        account,
        positions,
        quote.last,
        stop_price=stop_price,
        is_live=is_live,
    )
    print(verdict.message)
    if not verdict.allowed:
        print("Order not sent. Fix blockers or use paper mode to practice.")
        return
    if input("Submit order? (y/N): ").strip().lower() != "y":
        print("Canceled.")
        return

    if take_profit or stop_price:
        orders = broker.place_bracket(
            symbol, side, qty, take_profit=take_profit, stop_loss=stop_price
        )
        for o in orders:
            print(f"  {o.status.value}: {o.side.value} {o.qty} {o.symbol} id={o.id}")
    else:
        order = broker.place_order(req)
        print(
            f"Order {order.status.value}: {order.side.value} {order.qty} {order.symbol}"
            f" @ {order.filled_avg_price or 'resting'} id={order.id}"
        )


def trading_menu(user: str) -> None:
    settings = get_settings()
    broker = create_broker(user=user)
    print(f"\nConnected broker: {broker.profile.name} [{broker.profile.id}]")
    while True:
        print(
            "\n--- Trade Menu ---\n"
            "1. Account\n"
            "2. Positions\n"
            "3. Place order (with risk checks)\n"
            "4. Open orders\n"
            "5. Process paper stops\n"
            "6. Switch info (brokers list)\n"
            "7. Back\n"
        )
        choice = input("Choice: ").strip()
        try:
            if choice == "1":
                acct = broker.get_account()
                print(
                    f"Cash ${acct.cash:.2f} | Equity ${acct.equity:.2f} | "
                    f"BP ${acct.buying_power:.2f}"
                )
            elif choice == "2":
                for p in broker.list_positions():
                    print(
                        f"{p.symbol}: {p.qty} @ {p.avg_entry:.2f} "
                        f"MV ${p.market_value:.2f} uPL ${p.unrealized_pl:.2f}"
                    )
            elif choice == "3":
                _prompt_trade(broker, user)
            elif choice == "4":
                for o in broker.list_orders():
                    print(
                        f"{o.id[:8]} {o.status.value} {o.side.value} "
                        f"{o.qty} {o.symbol} {o.order_type.value}"
                    )
            elif choice == "5":
                if isinstance(broker, PaperBroker):
                    filled = broker.process_open_stops()
                    print(f"Triggered {len(filled)} stop(s)")
                else:
                    print("Stop processing is automatic at the live broker.")
            elif choice == "6":
                print(describe_brokers())
                print(f"\nCurrent INFOBROKER_BROKER={settings.broker}")
            elif choice == "7":
                break
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")


def research_menu() -> None:
    while True:
        print(
            "\n--- Research ---\n"
            "1. Quote\n"
            "2. History\n"
            "3. Fundamentals\n"
            "4. Backtest SMA crossover\n"
            "5. Back\n"
        )
        choice = input("Choice: ").strip()
        try:
            if choice == "1":
                symbol = input("Symbol: ").strip().upper()
                print(get_stock_quote(symbol))
            elif choice == "2":
                symbol = input("Symbol: ").strip().upper()
                start = input("Start YYYY-MM-DD: ").strip()
                end = input("End YYYY-MM-DD: ").strip()
                print(get_historical_data(symbol, start, end).tail(10))
            elif choice == "3":
                symbol = input("Symbol: ").strip().upper()
                print(get_fundamentals(symbol))
            elif choice == "4":
                symbol = input("Symbol: ").strip().upper()
                end = datetime.utcnow().date()
                start = end - timedelta(days=365)
                result = run_backtest(
                    symbol, start.isoformat(), end.isoformat()
                )
                print(
                    f"{result.symbol}: return {result.total_return_pct}% | "
                    f"max DD {result.max_drawdown_pct}% | trades {result.trades}"
                )
            elif choice == "5":
                break
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")


def learn_menu() -> None:
    while True:
        print("\n--- Learn ---")
        for i, lesson in enumerate(list_lessons(), 1):
            print(f"{i}. {lesson['title']}")
        print("0. Back")
        choice = input("Choice: ").strip()
        if choice == "0":
            break
        try:
            idx = int(choice) - 1
            summary = list_lessons()[idx]
            lesson = get_lesson(summary["id"]) or summary
            print(f"\n## {lesson['title']}")
            if lesson.get("level"):
                print(f"[{lesson['level']}] · {lesson.get('page_count', 1)} pages")
            pages = lesson.get("pages") or []
            if pages:
                for i, page in enumerate(pages, 1):
                    print(f"\n— Page {i}: {page.get('title', '')}")
                    if page.get("insight"):
                        print(f"Insight: {page['insight']}")
                    for section in page.get("sections") or []:
                        print(f"### {section['heading']}\n{section['text']}\n")
                    if page.get("quiz"):
                        print(f"Q: {page['quiz'].get('q')}\nA: {page['quiz'].get('a')}")
            else:
                print(f"\n{lesson.get('overview') or lesson.get('body')}\n")
                for section in lesson.get("sections") or []:
                    print(f"### {section['heading']}\n{section['text']}\n")
            if lesson.get("takeaways"):
                print("Takeaways:")
                for t in lesson["takeaways"]:
                    print(f"  - {t}")
            print()
        except (ValueError, IndexError):
            print("Invalid lesson")


def main_menu(user: str) -> None:
    while True:
        print(
            f"\n=== Infobroker ({user}) ===\n"
            "1. Learn (chart & risk lessons)\n"
            "2. Research (quotes, history, backtest)\n"
            "3. Trade (paper / live via broker)\n"
            "4. Broker ranking\n"
            "5. Log out\n"
        )
        choice = input("Choice: ").strip()
        if choice == "1":
            learn_menu()
        elif choice == "2":
            research_menu()
        elif choice == "3":
            trading_menu(user)
        elif choice == "4":
            print(describe_brokers())
        elif choice == "5":
            break


def main() -> None:
    migrate_legacy_users_json(ROOT / "users.json")
    settings = get_settings()
    print("Infobroker — teach, backtest, paper trade, live trade")
    print(f"Broker={settings.broker} | Data={settings.data_provider}")
    while True:
        print("\n1. Register\n2. Login\n3. Exit")
        choice = input("Choice: ").strip()
        if choice == "1":
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ")
            try:
                user = register(username, password)
                main_menu(user)
            except ValueError as exc:
                print(exc)
        elif choice == "2":
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ")
            user = login(username, password)
            if user:
                print(f"Welcome, {user}")
                main_menu(user)
            else:
                print("Login failed")
        elif choice == "3":
            print("Bye")
            break


if __name__ == "__main__":
    main()
