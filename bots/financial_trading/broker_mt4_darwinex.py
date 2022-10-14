""" Recieved events orders from Portfolio and send it to the broker or exchange for execution"""
from smartbots.brokerMQ import Emit_Events
from smartbots.events import Positions
import pytz
from smartbots.base_logger import logger


def main(send_orders_status=True):
    from smartbots.brokerMQ import receive_events
    import datetime as dt
    from smartbots.financial.darwinex_model import Trading
    import schedule
    from smartbots import conf
    from smartbots.health_handler import Health_Handler
    import time
    import threading

    def check_balance() -> None:
        try:
            balance = trading.get_balance()['_equity']
            print(f'Balance {balance} {dt.datetime.utcnow()}')
            health_handler.check()
        except Exception as e:
            logger.error(f'Error Getting Darwinex Balance: {e}')
            health_handler.send(description=e, state=0)

    def save_positions() -> None:
        try:
            positions = trading.get_account_positions()
            _d = dt.datetime.utcnow()
            dtime = dt.datetime(_d.year, _d.month, _d.day,
                                _d.hour, _d.minute, _d.second, 0, pytz.UTC)
            positions_event = Positions(ticker='real_positions_darwinex', account='darwinex_mt4_positions',
                                        positions=positions, datetime=dtime)
            emit.publish_event('positions', positions_event)

        except Exception as e:
            logger.error(f'Error Saving Darwinex Positions: {e}')

    def _schedule():
        # create scheduler for saving balance
        schedule.every(1).minutes.do(check_balance)
        schedule.every(15).seconds.do(save_positions)
        while True:
            schedule.run_pending()
            time.sleep(1)

    def send_broker(event) -> None:
        """Send order.

        Parameters
        ----------
        order: event order
        """
        if event.event_type == 'order' and conf.SEND_ORDERS_BROKER_DARWINEX == 1:
            event.exchange = 'mt4_darwinex'
            qtypes = {'buy': 1, 'sell': 0}  # the opposite position to the order
            symbol = event.ticker
            quantity = event.quantity
            open_trades = trading.get_trades()
            if open_trades is not None:
                trades_id = list(open_trades.keys())
                # Loop every trade
                for trade_id in trades_id:
                    trade = open_trades[trade_id]
                    # same symbol
                    if symbol == trade['_symbol']:
                        if trade['_type'] == qtypes[event.action]:
                            if quantity != 0:
                                if quantity > trade['_lots'] or quantity == trade['_lots']:
                                    # Close trade
                                    event.action_mt4 = 'close_trade'
                                    event.order_id_receiver = trade_id
                                    logger.info(
                                        f'Sending Order to close positions in ticker: {event.ticker} quantity: {event.quantity}')
                                    trading.send_order(event)
                                    quantity -= trade['_lots']
                                else:
                                    # Partially closed trade
                                    event.action_mt4 = 'close_partial'
                                    event.order_id_receiver = trade_id
                                    event.quantity = quantity
                                    logger.info(
                                        f'Sending Order to close partial positions in ticker: {event.ticker} quantity: {event.quantity}')
                                    trading.send_order(event)
                                    quantity = 0
                if quantity != 0:
                    logger.info(f'Sending Order to MT4 in ticker: {event.ticker} quantity: {event.quantity}')
                    event.quantity = quantity
                    event.action_mt4 = 'normal'
                    trading.send_order(event)

        elif event.event_type == 'order' and conf.SEND_ORDERS_BROKER_DARWINEX == 0:
            event.exchange = 'mt4_darwinex'
            print(f'Order for {event.ticker} recieved but not send.')

    # Log event health of the service
    health_handler = Health_Handler(n_check=4,
                                    name_service='mt4_darwinex')

    # Create trading object
    trading = Trading(send_orders_status=send_orders_status, type_service='broker')
    check_balance()
    # Launch thread to saving health and saving positions
    x = threading.Thread(target=_schedule)
    x.start()
    # Launch thead for update orders status
    trading.start_update_orders_status()
    emit = Emit_Events()
    receive_events(routing_key='financial_order', callback=send_broker)


if __name__ == '__main__':
    main()