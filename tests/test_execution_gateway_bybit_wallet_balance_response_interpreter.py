from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_wallet_balance_response_interpreter import (
    BybitWalletBalanceResponseInterpreter,
)
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot


def _coin_item(**overrides):
    defaults = dict(
        coin="USDT",
        walletBalance="1000.5",
        equity="1005.25",
        unrealisedPnl="4.75",
        usdValue="1005.25",
    )
    defaults.update(overrides)
    return defaults


def _account_item(**overrides):
    defaults = dict(
        accountType="UNIFIED",
        totalEquity="1005.25",
        totalWalletBalance="1000.5",
        totalAvailableBalance="800.0",
        totalInitialMargin="200.5",
        totalMaintenanceMargin="50.25",
        coin=(_coin_item(),),
    )
    defaults.update(overrides)
    return defaults


def _response(*, ret_code=0, ret_msg="OK", accounts=None, time_ms=1_700_000_000_000, result_override=None):
    if result_override is not None:
        result = result_override
    else:
        result = {"list": tuple(accounts if accounts is not None else (_account_item(),))}
    return BybitResponse(ret_code=ret_code, ret_msg=ret_msg, result=result, ret_ext_info={}, time_ms=time_ms)


def _interpret(**kwargs):
    return BybitWalletBalanceResponseInterpreter().interpret(response=_response(**kwargs))


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitWalletBalanceResponseInterpreter")
        assert (
            execution_gateway.BybitWalletBalanceResponseInterpreter
            is BybitWalletBalanceResponseInterpreter
        )

    def test_in_all(self):
        assert "BybitWalletBalanceResponseInterpreter" in execution_gateway.__all__


class TestInputValidation:
    def test_response_must_be_bybit_response(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            BybitWalletBalanceResponseInterpreter().interpret(response={"retCode": 0})


class TestApiError:
    def test_nonzero_ret_code_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError) as exc_info:
            _interpret(ret_code=10003, ret_msg="API key is invalid")
        assert exc_info.value.ret_code == 10003

    def test_ret_code_checked_before_touching_result(self):
        with pytest.raises(BybitApiError):
            _interpret(ret_code=10004, ret_msg="error sign", result_override="not-a-mapping")


class TestAccountTotals:
    def test_returns_wallet_balance_snapshot(self):
        snapshot = _interpret()
        assert isinstance(snapshot, WalletBalanceSnapshot)

    def test_total_equity_mapped(self):
        snapshot = _interpret(accounts=[_account_item(totalEquity="12345.6789")])
        assert snapshot.total_equity == Decimal("12345.6789")

    def test_total_wallet_balance_mapped(self):
        snapshot = _interpret(accounts=[_account_item(totalWalletBalance="9999.99")])
        assert snapshot.total_wallet_balance == Decimal("9999.99")

    def test_total_available_balance_mapped(self):
        snapshot = _interpret(accounts=[_account_item(totalAvailableBalance="500.25")])
        assert snapshot.total_available_balance == Decimal("500.25")

    def test_total_initial_margin_mapped(self):
        snapshot = _interpret(accounts=[_account_item(totalInitialMargin="100")])
        assert snapshot.total_initial_margin == Decimal("100")

    def test_total_maintenance_margin_mapped(self):
        snapshot = _interpret(accounts=[_account_item(totalMaintenanceMargin="25")])
        assert snapshot.total_maintenance_margin == Decimal("25")

    def test_total_initial_margin_zero_is_valid(self):
        # Cuenta flat (sin posiciones/órdenes abiertas): margen usado "0" es
        # el valor legítimo, no ausencia.
        snapshot = _interpret(accounts=[_account_item(totalInitialMargin="0", totalMaintenanceMargin="0")])
        assert snapshot.total_initial_margin == Decimal("0")
        assert snapshot.total_maintenance_margin == Decimal("0")

    def test_negative_total_equity_accepted(self):
        # Escenario de pérdidas -- no se asume que equity nunca es negativo.
        snapshot = _interpret(accounts=[_account_item(totalEquity="-50.5")])
        assert snapshot.total_equity == Decimal("-50.5")

    def test_server_time_populated_from_response(self):
        snapshot = _interpret(time_ms=1_712_345_678_901)
        assert snapshot.server_time_ms == 1_712_345_678_901

    def test_account_type_field_not_used_not_required(self):
        item = _account_item()
        del item["accountType"]
        snapshot = _interpret(accounts=[item])
        assert isinstance(snapshot, WalletBalanceSnapshot)


class TestCurrencyBalances:
    def test_single_currency_mapped(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(coin="USDT"),))])
        assert len(snapshot.currency_balances) == 1
        assert snapshot.currency_balances[0].coin == "USDT"

    def test_multiple_currencies_preserved(self):
        coins = (_coin_item(coin="USDT"), _coin_item(coin="USDC"))
        snapshot = _interpret(accounts=[_account_item(coin=coins)])
        assert {b.coin for b in snapshot.currency_balances} == {"USDT", "USDC"}

    def test_unknown_currency_not_discarded(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(coin="SHIB"),))])
        assert snapshot.currency_balances[0].coin == "SHIB"

    def test_empty_coin_list_is_valid_empty_snapshot(self):
        # Cuenta sin ninguna moneda con saldo no-cero: conceptualmente
        # válido, Bybit omite monedas en cero.
        snapshot = _interpret(accounts=[_account_item(coin=())])
        assert snapshot.currency_balances == ()

    def test_wallet_balance_mapped(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(walletBalance="42.5"),))])
        assert snapshot.currency_balances[0].wallet_balance == Decimal("42.5")

    def test_equity_mapped(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(equity="43.75"),))])
        assert snapshot.currency_balances[0].equity == Decimal("43.75")

    def test_deterministic_order_matches_input(self):
        coins = (_coin_item(coin="USDT"), _coin_item(coin="USDC"), _coin_item(coin="BTC"))
        snapshot = _interpret(accounts=[_account_item(coin=coins)])
        assert [b.coin for b in snapshot.currency_balances] == ["USDT", "USDC", "BTC"]


class TestZeroAndEmptySemantics:
    """Aplica explícitamente las lecciones de 3.70/3.71: un campo accesorio
    vacío o "0" en una respuesta legítima de Bybit no debe abortar el
    snapshot completo."""

    def test_unrealised_pnl_empty_string_becomes_none(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(unrealisedPnl=""),))])
        assert snapshot.currency_balances[0].unrealized_pnl is None

    def test_unrealised_pnl_missing_key_becomes_none(self):
        item = _coin_item()
        del item["unrealisedPnl"]
        snapshot = _interpret(accounts=[_account_item(coin=(item,))])
        assert snapshot.currency_balances[0].unrealized_pnl is None

    def test_unrealised_pnl_zero_is_preserved_as_zero_not_none(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(unrealisedPnl="0"),))])
        assert snapshot.currency_balances[0].unrealized_pnl == Decimal("0")

    def test_unrealised_pnl_malformed_non_empty_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(_coin_item(unrealisedPnl="not-a-number"),))])

    def test_usd_value_empty_string_becomes_none(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(usdValue=""),))])
        assert snapshot.currency_balances[0].usd_value is None

    def test_usd_value_missing_key_becomes_none(self):
        item = _coin_item()
        del item["usdValue"]
        snapshot = _interpret(accounts=[_account_item(coin=(item,))])
        assert snapshot.currency_balances[0].usd_value is None

    def test_usd_value_zero_is_preserved_as_zero_not_none(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(usdValue="0"),))])
        assert snapshot.currency_balances[0].usd_value == Decimal("0")

    def test_usd_value_malformed_non_empty_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(_coin_item(usdValue="abc"),))])

    def test_accessory_empty_among_valid_currencies_does_not_abort_snapshot(self):
        coins = (
            _coin_item(coin="USDT", unrealisedPnl="", usdValue=""),
            _coin_item(coin="USDC", unrealisedPnl="1.5", usdValue="1.5"),
        )
        snapshot = _interpret(accounts=[_account_item(coin=coins)])
        assert len(snapshot.currency_balances) == 2
        by_coin = {b.coin: b for b in snapshot.currency_balances}
        assert by_coin["USDT"].unrealized_pnl is None
        assert by_coin["USDC"].unrealized_pnl == Decimal("1.5")

    def test_wallet_balance_zero_preserved_not_rejected(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(walletBalance="0"),))])
        assert snapshot.currency_balances[0].wallet_balance == Decimal("0")

    def test_equity_zero_preserved_not_rejected(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(equity="0"),))])
        assert snapshot.currency_balances[0].equity == Decimal("0")


class TestNumerics:
    def test_high_precision_decimal_preserved(self):
        snapshot = _interpret(accounts=[_account_item(totalEquity="12345.123456789")])
        assert snapshot.total_equity == Decimal("12345.123456789")

    def test_very_small_number_preserved(self):
        snapshot = _interpret(accounts=[_account_item(coin=(_coin_item(walletBalance="0.00000001"),))])
        assert snapshot.currency_balances[0].wallet_balance == Decimal("0.00000001")

    def test_very_large_number_preserved(self):
        snapshot = _interpret(accounts=[_account_item(totalEquity="99999999999.99")])
        assert snapshot.total_equity == Decimal("99999999999.99")

    def test_never_silently_converts_to_float(self):
        snapshot = _interpret(accounts=[_account_item(totalEquity="0.1")])
        assert isinstance(snapshot.total_equity, Decimal)
        assert snapshot.total_equity == Decimal("0.1")

    def test_nan_total_equity_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(totalEquity="nan")])

    def test_infinity_total_equity_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(totalEquity="inf")])

    def test_nan_wallet_balance_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(_coin_item(walletBalance="nan"),))])

    def test_infinity_equity_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(_coin_item(equity="inf"),))])

    def test_negative_total_initial_margin_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(totalInitialMargin="-1")])

    def test_negative_total_maintenance_margin_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(totalMaintenanceMargin="-1")])


class TestMalformedResponse:
    def test_result_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override="not-a-mapping")

    def test_result_list_key_missing(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={})

    def test_list_not_a_tuple(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"list": "not-a-list"})

    def test_list_item_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"list": ("not-a-dict",)})

    def test_empty_list_rejected(self):
        # accountType=UNIFIED consultado -> se espera exactamente 1 cuenta;
        # 0 elementos es una forma no modelada.
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"list": ()})

    def test_multiple_accounts_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"list": (_account_item(), _account_item())})

    def test_total_equity_missing(self):
        item = _account_item()
        del item["totalEquity"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[item])

    def test_total_wallet_balance_missing(self):
        item = _account_item()
        del item["totalWalletBalance"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[item])

    def test_total_available_balance_missing(self):
        item = _account_item()
        del item["totalAvailableBalance"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[item])

    def test_total_initial_margin_missing(self):
        item = _account_item()
        del item["totalInitialMargin"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[item])

    def test_total_maintenance_margin_missing(self):
        item = _account_item()
        del item["totalMaintenanceMargin"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[item])

    def test_coin_key_missing(self):
        item = _account_item()
        del item["coin"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[item])

    def test_coin_not_a_tuple(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin="not-a-tuple")])

    def test_total_equity_empty_string_rejected(self):
        # totalEquity es esencial (razón de ser del hito) -- a diferencia
        # de unrealisedPnl/usdValue, un total en blanco falla cerrado.
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(totalEquity="")])

    def test_total_wallet_balance_malformed_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(totalWalletBalance="abc")])

    def test_coin_item_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=("not-a-dict",))])

    def test_currency_coin_field_missing(self):
        item = _coin_item()
        del item["coin"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(item,))])

    def test_currency_coin_field_invalid_type(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(_coin_item(coin=123),))])

    def test_currency_wallet_balance_missing(self):
        item = _coin_item()
        del item["walletBalance"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(item,))])

    def test_currency_wallet_balance_malformed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(_coin_item(walletBalance="abc"),))])

    def test_currency_equity_missing(self):
        item = _coin_item()
        del item["equity"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(item,))])

    def test_currency_equity_malformed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=(_coin_item(equity="xyz"),))])

    def test_one_malformed_currency_among_valid_ones_fails_closed(self):
        coins = (_coin_item(coin="USDT"), _coin_item(coin="USDC", equity="not-a-number"))
        with pytest.raises(BybitResponseProcessingError):
            _interpret(accounts=[_account_item(coin=coins)])


class TestNoPaginationConcept:
    def test_no_pagination_follow_up_implemented(self):
        import inspect
        import execution_gateway.bybit_wallet_balance_response_interpreter as module
        src = inspect.getsource(module)
        assert "urllib" not in src
        assert "urlopen" not in src

    def test_no_next_page_cursor_check_in_source(self):
        # /v5/account/wallet-balance no documenta nextPageCursor -- a
        # diferencia de Positions/Open Orders Read, no se inventa un
        # cheque de paginación para un campo que no existe en este esquema.
        import inspect
        import execution_gateway.bybit_wallet_balance_response_interpreter as module
        src = inspect.getsource(module)
        assert 'result.get("nextPageCursor")' not in src

    def test_presence_of_unexpected_next_page_cursor_key_is_ignored(self):
        # Si Bybit alguna vez agregara esta clave inesperadamente, no debe
        # tener ningún efecto especial -- no se lee en absoluto.
        item = _account_item()
        result_with_cursor = {"list": (item,), "nextPageCursor": "unexpected"}
        snapshot = _interpret(result_override=result_with_cursor)
        assert isinstance(snapshot, WalletBalanceSnapshot)


class TestPurity:
    def test_public_contract_does_not_expose_bybit_vocabulary(self):
        snapshot = _interpret()
        public = {k for k in vars(snapshot) if not k.startswith("_")}
        forbidden = {"retCode", "retMsg", "totalEquity", "totalWalletBalance", "accountType"}
        assert public.isdisjoint(forbidden)

    def test_no_raw_dict_leaks_into_snapshot(self):
        snapshot = _interpret()
        assert not hasattr(snapshot, "result")
        assert not hasattr(snapshot, "raw")
