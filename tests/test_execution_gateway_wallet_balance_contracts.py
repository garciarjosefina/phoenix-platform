import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.wallet_balance_contracts import ExecutionCurrencyBalance, WalletBalanceSnapshot


def _balance(**overrides):
    defaults = dict(
        coin="USDT",
        wallet_balance=Decimal("1000.5"),
        equity=Decimal("1005.25"),
        unrealized_pnl=Decimal("4.75"),
        usd_value=Decimal("1005.25"),
    )
    defaults.update(overrides)
    return ExecutionCurrencyBalance(**defaults)


def _snapshot(**overrides):
    defaults = dict(
        total_equity=Decimal("1005.25"),
        total_wallet_balance=Decimal("1000.5"),
        total_available_balance=Decimal("800.0"),
        total_initial_margin=Decimal("200.5"),
        total_maintenance_margin=Decimal("50.25"),
        currency_balances=(_balance(),),
        server_time_ms=1_700_000_000_000,
    )
    defaults.update(overrides)
    return WalletBalanceSnapshot(**defaults)


class TestImport:
    def test_execution_currency_balance_importable_from_package(self):
        assert hasattr(execution_gateway, "ExecutionCurrencyBalance")
        assert execution_gateway.ExecutionCurrencyBalance is ExecutionCurrencyBalance

    def test_execution_currency_balance_in_all(self):
        assert "ExecutionCurrencyBalance" in execution_gateway.__all__

    def test_wallet_balance_snapshot_importable_from_package(self):
        assert hasattr(execution_gateway, "WalletBalanceSnapshot")
        assert execution_gateway.WalletBalanceSnapshot is WalletBalanceSnapshot

    def test_wallet_balance_snapshot_in_all(self):
        assert "WalletBalanceSnapshot" in execution_gateway.__all__


class TestExecutionCurrencyBalanceContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExecutionCurrencyBalance)
        assert ExecutionCurrencyBalance.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExecutionCurrencyBalance)]
        assert names == ["coin", "wallet_balance", "equity", "unrealized_pnl", "usd_value"]

    def test_cannot_reassign_field(self):
        balance = _balance()
        with pytest.raises(Exception):
            balance.wallet_balance = Decimal("0")

    def test_no_bybit_types_in_public_attributes(self):
        balance = _balance()
        public = {k for k in vars(balance) if not k.startswith("_")}
        forbidden = {"walletBalance", "unrealisedPnl", "usdValue", "retCode", "retMsg"}
        assert public.isdisjoint(forbidden)

    def test_rejects_extra_field(self):
        with pytest.raises(TypeError):
            _balance(retCode=0)

    # ── coin ─────────────────────────────────────────────────────────────

    def test_coin_must_be_str(self):
        with pytest.raises(TypeError, match="coin must be str"):
            _balance(coin=1)

    def test_coin_must_not_be_empty(self):
        with pytest.raises(ValueError, match="coin must not be empty"):
            _balance(coin="")

    def test_coin_must_not_be_whitespace_only(self):
        with pytest.raises(ValueError, match="coin must not be empty"):
            _balance(coin="   ")

    def test_coin_always_required_no_default(self):
        with pytest.raises(TypeError):
            ExecutionCurrencyBalance(wallet_balance=Decimal("1"), equity=Decimal("1"))

    # ── wallet_balance / equity ─────────────────────────────────────────

    def test_wallet_balance_must_be_decimal(self):
        with pytest.raises(TypeError, match="wallet_balance must be Decimal"):
            _balance(wallet_balance=1000.5)

    def test_wallet_balance_rejects_nan(self):
        with pytest.raises(ValueError, match="wallet_balance must be finite"):
            _balance(wallet_balance=Decimal("nan"))

    def test_wallet_balance_zero_is_valid(self):
        balance = _balance(wallet_balance=Decimal("0"))
        assert balance.wallet_balance == Decimal("0")

    def test_wallet_balance_negative_is_valid(self):
        # Sin restricción de signo -- no se asume una regla de negocio no
        # confirmada por la documentación de Bybit.
        balance = _balance(wallet_balance=Decimal("-5"))
        assert balance.wallet_balance == Decimal("-5")

    def test_equity_must_be_decimal(self):
        with pytest.raises(TypeError, match="equity must be Decimal"):
            _balance(equity=1005.25)

    def test_equity_rejects_nan(self):
        with pytest.raises(ValueError, match="equity must be finite"):
            _balance(equity=Decimal("nan"))

    def test_equity_negative_is_valid(self):
        balance = _balance(equity=Decimal("-10.5"))
        assert balance.equity == Decimal("-10.5")

    # ── unrealized_pnl / usd_value (accesorios) ─────────────────────────

    def test_unrealized_pnl_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionCurrencyBalance) if f.name == "unrealized_pnl")
        assert field.default is None

    def test_unrealized_pnl_none_is_valid(self):
        balance = _balance(unrealized_pnl=None)
        assert balance.unrealized_pnl is None

    def test_unrealized_pnl_negative_is_valid(self):
        # MENOR-2 (auditoría post-3.72): una posición perdedora es el caso
        # más común del mundo real -- protección explícita contra una
        # futura regresión que agregue una validación >=0 sin evidencia.
        balance = _balance(unrealized_pnl=Decimal("-4.75"))
        assert balance.unrealized_pnl == Decimal("-4.75")

    def test_usd_value_negative_is_valid(self):
        # MENOR-2 (auditoría post-3.72): mismo principio -- usd_value sigue
        # el signo del activo subyacente, no hay evidencia de que Bybit
        # garantice no-negatividad.
        balance = _balance(usd_value=Decimal("-100.5"))
        assert balance.usd_value == Decimal("-100.5")

    def test_unrealized_pnl_zero_is_valid(self):
        balance = _balance(unrealized_pnl=Decimal("0"))
        assert balance.unrealized_pnl == Decimal("0")

    def test_unrealized_pnl_must_be_decimal_when_present(self):
        with pytest.raises(TypeError, match="unrealized_pnl must be Decimal or None"):
            _balance(unrealized_pnl=4.75)

    def test_unrealized_pnl_rejects_nan(self):
        with pytest.raises(ValueError, match="unrealized_pnl must be finite"):
            _balance(unrealized_pnl=Decimal("nan"))

    def test_usd_value_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionCurrencyBalance) if f.name == "usd_value")
        assert field.default is None

    def test_usd_value_none_is_valid(self):
        balance = _balance(usd_value=None)
        assert balance.usd_value is None

    def test_usd_value_zero_is_valid(self):
        balance = _balance(usd_value=Decimal("0"))
        assert balance.usd_value == Decimal("0")

    def test_usd_value_must_be_decimal_when_present(self):
        with pytest.raises(TypeError, match="usd_value must be Decimal or None"):
            _balance(usd_value=1005.25)

    def test_usd_value_rejects_nan(self):
        with pytest.raises(ValueError, match="usd_value must be finite"):
            _balance(usd_value=Decimal("nan"))

    # ── superficie / equality ───────────────────────────────────────────

    def test_repr_does_not_crash(self):
        text = repr(_balance())
        assert "USDT" in text

    def test_equality_by_value(self):
        assert _balance() == _balance()

    def test_inequality_on_different_coin(self):
        assert _balance(coin="USDT") != _balance(coin="USDC")


class TestWalletBalanceSnapshotContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(WalletBalanceSnapshot)
        assert WalletBalanceSnapshot.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(WalletBalanceSnapshot)]
        assert names == [
            "total_equity", "total_wallet_balance", "total_available_balance",
            "total_initial_margin", "total_maintenance_margin",
            "currency_balances", "server_time_ms",
        ]

    def test_cannot_reassign_field(self):
        snapshot = _snapshot()
        with pytest.raises(Exception):
            snapshot.total_equity = Decimal("0")

    def test_no_bybit_types_in_public_attributes(self):
        snapshot = _snapshot()
        public = {k for k in vars(snapshot) if not k.startswith("_")}
        forbidden = {"totalEquity", "totalWalletBalance", "accountType", "retCode"}
        assert public.isdisjoint(forbidden)

    def test_rejects_extra_field(self):
        with pytest.raises(TypeError):
            _snapshot(accountType="UNIFIED")

    # ── total_equity / total_wallet_balance / total_available_balance ──

    def test_total_equity_must_be_decimal(self):
        with pytest.raises(TypeError, match="total_equity must be Decimal"):
            _snapshot(total_equity=1005.25)

    def test_total_equity_rejects_nan(self):
        with pytest.raises(ValueError, match="total_equity must be finite"):
            _snapshot(total_equity=Decimal("nan"))

    def test_total_equity_negative_is_valid(self):
        snapshot = _snapshot(total_equity=Decimal("-100"))
        assert snapshot.total_equity == Decimal("-100")

    def test_total_wallet_balance_must_be_decimal(self):
        with pytest.raises(TypeError, match="total_wallet_balance must be Decimal"):
            _snapshot(total_wallet_balance=1000.5)

    def test_total_wallet_balance_rejects_nan(self):
        with pytest.raises(ValueError, match="total_wallet_balance must be finite"):
            _snapshot(total_wallet_balance=Decimal("nan"))

    def test_total_available_balance_must_be_decimal(self):
        with pytest.raises(TypeError, match="total_available_balance must be Decimal"):
            _snapshot(total_available_balance=800.0)

    def test_total_available_balance_rejects_nan(self):
        with pytest.raises(ValueError, match="total_available_balance must be finite"):
            _snapshot(total_available_balance=Decimal("nan"))

    def test_total_available_balance_negative_is_valid(self):
        # Escenario cercano a liquidación -- no se asume que nunca puede
        # volverse negativo.
        snapshot = _snapshot(total_available_balance=Decimal("-1"))
        assert snapshot.total_available_balance == Decimal("-1")

    # ── total_initial_margin / total_maintenance_margin (>= 0) ─────────

    def test_total_initial_margin_must_be_decimal(self):
        with pytest.raises(TypeError, match="total_initial_margin must be Decimal"):
            _snapshot(total_initial_margin=200.5)

    def test_total_initial_margin_zero_is_valid(self):
        snapshot = _snapshot(total_initial_margin=Decimal("0"))
        assert snapshot.total_initial_margin == Decimal("0")

    def test_total_initial_margin_rejects_negative(self):
        with pytest.raises(ValueError, match="total_initial_margin must be >= 0"):
            _snapshot(total_initial_margin=Decimal("-1"))

    def test_total_initial_margin_rejects_nan(self):
        with pytest.raises(ValueError, match="total_initial_margin must be finite"):
            _snapshot(total_initial_margin=Decimal("nan"))

    def test_total_maintenance_margin_must_be_decimal(self):
        with pytest.raises(TypeError, match="total_maintenance_margin must be Decimal"):
            _snapshot(total_maintenance_margin=50.25)

    def test_total_maintenance_margin_zero_is_valid(self):
        snapshot = _snapshot(total_maintenance_margin=Decimal("0"))
        assert snapshot.total_maintenance_margin == Decimal("0")

    def test_total_maintenance_margin_rejects_negative(self):
        with pytest.raises(ValueError, match="total_maintenance_margin must be >= 0"):
            _snapshot(total_maintenance_margin=Decimal("-1"))

    def test_total_maintenance_margin_rejects_nan(self):
        with pytest.raises(ValueError, match="total_maintenance_margin must be finite"):
            _snapshot(total_maintenance_margin=Decimal("nan"))

    # ── currency_balances ────────────────────────────────────────────────

    def test_empty_currency_balances_is_valid(self):
        # Snapshot conceptualmente vacío: cuenta sin ninguna moneda con
        # saldo no-cero (Bybit omite monedas en cero por defecto).
        snapshot = _snapshot(currency_balances=())
        assert snapshot.currency_balances == ()

    def test_currency_balances_must_be_tuple(self):
        with pytest.raises(TypeError, match="currency_balances must be tuple"):
            _snapshot(currency_balances=[_balance()])

    def test_currency_balances_items_must_be_execution_currency_balance(self):
        with pytest.raises(TypeError, match="ExecutionCurrencyBalance"):
            _snapshot(currency_balances=({"coin": "USDT"},))

    def test_multiple_currencies_preserved(self):
        usdt = _balance(coin="USDT")
        usdc = _balance(coin="USDC")
        snapshot = _snapshot(currency_balances=(usdt, usdc))
        assert len(snapshot.currency_balances) == 2

    def test_unknown_currency_not_rejected_at_contract_level(self):
        # El contrato no filtra por un set cerrado de monedas conocidas --
        # eso sería descartar en silencio una moneda inesperada.
        exotic = _balance(coin="SHIB")
        snapshot = _snapshot(currency_balances=(exotic,))
        assert snapshot.currency_balances[0].coin == "SHIB"

    # ── server_time_ms ───────────────────────────────────────────────────

    def test_server_time_ms_must_be_int(self):
        with pytest.raises(TypeError, match="server_time_ms must be int"):
            _snapshot(server_time_ms=1.5)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError, match="server_time_ms must be >= 0"):
            _snapshot(server_time_ms=-1)

    def test_cannot_reassign_currency_balances(self):
        snapshot = _snapshot()
        with pytest.raises(Exception):
            snapshot.currency_balances = ()

    def test_no_bybit_types_leak_via_vars(self):
        snapshot = _snapshot()
        public = {k for k in vars(snapshot) if not k.startswith("_")}
        assert public == {
            "total_equity", "total_wallet_balance", "total_available_balance",
            "total_initial_margin", "total_maintenance_margin",
            "currency_balances", "server_time_ms",
        }


class TestPurityByAst:
    """No basta con buscar strings -- se auditan los imports reales vía AST
    para confirmar que el contrato de dominio es exchange-agnostic: sin
    Bybit, sin urllib/HTTP, sin config específica del exchange."""

    _FORBIDDEN_SUBSTRINGS = ("bybit", "urllib", "http", "requests", "socket")

    def _module_imports(self, module) -> list[str]:
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(module))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        return names

    def test_contracts_module_has_no_forbidden_imports(self):
        import execution_gateway.wallet_balance_contracts as module
        imports = self._module_imports(module)
        violations = [i for i in imports if any(f in i.lower() for f in self._FORBIDDEN_SUBSTRINGS)]
        assert violations == []

    def test_contracts_module_imports_are_stdlib_only(self):
        import execution_gateway.wallet_balance_contracts as module
        imports = self._module_imports(module)
        assert set(imports) == {"dataclasses", "decimal"}

    def test_reader_protocol_module_has_no_forbidden_imports(self):
        import execution_gateway.wallet_balance_reader as module
        imports = self._module_imports(module)
        violations = [i for i in imports if any(f in i.lower() for f in self._FORBIDDEN_SUBSTRINGS)]
        assert violations == []

    def test_reader_protocol_module_only_imports_typing_and_own_contract(self):
        import execution_gateway.wallet_balance_reader as module
        imports = self._module_imports(module)
        assert set(imports) == {"typing", "execution_gateway.wallet_balance_contracts"}


class TestTotalAvailableBalanceSemantics:
    """IMPORTANTE-2 (auditoría post-3.72): total_available_balance NO es
    buying power en USDT ni "lo que puede usarse para abrir una posición
    nueva" -- es una magnitud de cuenta en equivalente USD, neta de un
    Haircut no definido por Bybit, dependiente del margin mode, que agrega
    todos los activos de colateral. Estos tests documentan que el contrato
    NO impone ninguna relación con el balance de USDT específicamente --
    imponer una no sería fiel a la semántica remota real."""

    def test_can_exceed_any_single_currency_wallet_balance(self):
        # No hay invariante que ate total_available_balance al balance de
        # ninguna moneda particular -- es coherente con ser una magnitud
        # agregada multi-activo, no un espejo de USDT.
        usdt = _balance(coin="USDT", wallet_balance=Decimal("10"))
        snapshot = _snapshot(total_available_balance=Decimal("99999"), currency_balances=(usdt,))
        assert snapshot.total_available_balance == Decimal("99999")

    def test_can_be_less_than_any_single_currency_wallet_balance(self):
        usdt = _balance(coin="USDT", wallet_balance=Decimal("99999"))
        snapshot = _snapshot(total_available_balance=Decimal("1"), currency_balances=(usdt,))
        assert snapshot.total_available_balance == Decimal("1")

    def test_valid_with_zero_currency_balances(self):
        # total_available_balance es un campo de CUENTA, no depende de que
        # currency_balances tenga contenido -- refuerza que no es un
        # "espejo" de ningún balance por moneda.
        snapshot = _snapshot(total_available_balance=Decimal("500"), currency_balances=())
        assert snapshot.total_available_balance == Decimal("500")

    def test_no_relationship_enforced_with_usdt_coin_presence(self):
        # Snapshot sin ninguna entrada USDT sigue siendo válido con
        # total_available_balance positivo -- el campo no exige que exista
        # una fila USDT correspondiente.
        non_usdt = _balance(coin="BTC")
        snapshot = _snapshot(total_available_balance=Decimal("42"), currency_balances=(non_usdt,))
        assert snapshot.total_available_balance == Decimal("42")
        assert all(b.coin != "USDT" for b in snapshot.currency_balances)


class TestCurrencyBalancesDuplicatesNotRejectedAtContractLevel:
    """MENOR-3 (auditoría post-3.72): el contrato es una tupla simple --
    no impone unicidad de `coin`. La deduplicación (o su rechazo) es una
    decisión del interpreter, no del contrato de dominio; verificado aquí
    para que una futura restricción de unicidad en el contrato mismo sea
    una decisión deliberada, no un efecto colateral accidental."""

    def test_duplicate_coin_entries_both_preserved(self):
        a = _balance(coin="USDT", wallet_balance=Decimal("1"))
        b = _balance(coin="USDT", wallet_balance=Decimal("2"))
        snapshot = _snapshot(currency_balances=(a, b))
        assert len(snapshot.currency_balances) == 2
        assert snapshot.currency_balances[0].wallet_balance == Decimal("1")
        assert snapshot.currency_balances[1].wallet_balance == Decimal("2")
