import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.instrument_metadata_contracts import ExecutionInstrumentMetadata


def _metadata(**overrides):
    defaults = dict(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        settlement_asset="USDT",
        instrument_status="Trading",
        contract_type="LinearPerpetual",
        tick_size=Decimal("0.10"),
        min_price=Decimal("0.10"),
        max_price=Decimal("1999999.80"),
        qty_step=Decimal("0.001"),
        min_order_qty=Decimal("0.001"),
        max_order_qty=Decimal("1190.000"),
        server_time_ms=1_700_000_000_000,
        max_market_order_qty=Decimal("500.000"),
        min_notional_value=Decimal("5"),
        min_leverage=Decimal("1"),
        max_leverage=Decimal("100.00"),
        leverage_step=Decimal("0.01"),
    )
    defaults.update(overrides)
    return ExecutionInstrumentMetadata(**defaults)


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "ExecutionInstrumentMetadata")
        assert execution_gateway.ExecutionInstrumentMetadata is ExecutionInstrumentMetadata

    def test_in_all(self):
        assert "ExecutionInstrumentMetadata" in execution_gateway.__all__


class TestExecutionInstrumentMetadataContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExecutionInstrumentMetadata)
        assert ExecutionInstrumentMetadata.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExecutionInstrumentMetadata)]
        assert names == [
            "symbol", "base_asset", "quote_asset", "settlement_asset",
            "instrument_status", "contract_type",
            "tick_size", "min_price", "max_price",
            "qty_step", "min_order_qty", "max_order_qty", "server_time_ms",
            "max_market_order_qty", "min_notional_value",
            "min_leverage", "max_leverage", "leverage_step",
        ]

    def test_cannot_reassign_field(self):
        metadata = _metadata()
        with pytest.raises(Exception):
            metadata.symbol = "ETHUSDT"

    def test_no_bybit_types_in_public_attributes(self):
        metadata = _metadata()
        public = {k for k in vars(metadata) if not k.startswith("_")}
        forbidden = {"baseCoin", "quoteCoin", "settleCoin", "status", "contractType",
                     "priceFilter", "lotSizeFilter", "leverageFilter", "retCode"}
        assert public.isdisjoint(forbidden)

    def test_rejects_extra_field(self):
        with pytest.raises(TypeError):
            _metadata(retCode=0)

    # ── symbol / base_asset / quote_asset / settlement_asset ────────────

    def test_symbol_must_be_str(self):
        with pytest.raises(TypeError, match="symbol must be str"):
            _metadata(symbol=1)

    def test_symbol_must_not_be_empty(self):
        with pytest.raises(ValueError, match="symbol must not be empty"):
            _metadata(symbol="")

    def test_symbol_always_required_no_default(self):
        with pytest.raises(TypeError):
            ExecutionInstrumentMetadata(
                base_asset="BTC", quote_asset="USDT", settlement_asset="USDT",
                instrument_status="Trading", contract_type="LinearPerpetual",
                tick_size=Decimal("0.1"), min_price=Decimal("0.1"), max_price=Decimal("100"),
                qty_step=Decimal("0.1"), min_order_qty=Decimal("0.1"), max_order_qty=Decimal("100"),
                server_time_ms=1,
            )

    def test_base_asset_must_be_str(self):
        with pytest.raises(TypeError, match="base_asset must be str"):
            _metadata(base_asset=1)

    def test_base_asset_must_not_be_empty(self):
        with pytest.raises(ValueError, match="base_asset must not be empty"):
            _metadata(base_asset="")

    def test_quote_asset_must_be_str(self):
        with pytest.raises(TypeError, match="quote_asset must be str"):
            _metadata(quote_asset=1)

    def test_quote_asset_must_not_be_empty(self):
        with pytest.raises(ValueError, match="quote_asset must not be empty"):
            _metadata(quote_asset="")

    def test_settlement_asset_must_be_str(self):
        with pytest.raises(TypeError, match="settlement_asset must be str"):
            _metadata(settlement_asset=1)

    def test_settlement_asset_must_not_be_empty(self):
        with pytest.raises(ValueError, match="settlement_asset must not be empty"):
            _metadata(settlement_asset="")

    def test_settlement_asset_distinct_from_quote_asset_allowed(self):
        # Coin-margined hipotético -- el contrato no impone que coincidan;
        # es información remota observada, no una regla inventada.
        metadata = _metadata(quote_asset="USD", settlement_asset="BTC")
        assert metadata.quote_asset != metadata.settlement_asset

    # ── instrument_status / contract_type (sin enum cerrado) ────────────

    def test_instrument_status_must_be_str(self):
        with pytest.raises(TypeError, match="instrument_status must be str"):
            _metadata(instrument_status=1)

    def test_instrument_status_must_not_be_empty(self):
        with pytest.raises(ValueError, match="instrument_status must not be empty"):
            _metadata(instrument_status="")

    def test_instrument_status_preserves_bybit_casing(self):
        # Deliberado: sin traducción a minúsculas ni a un enum cerrado --
        # ver instrument_metadata_contracts.py.
        metadata = _metadata(instrument_status="Trading")
        assert metadata.instrument_status == "Trading"

    def test_instrument_status_accepts_unanticipated_value(self):
        # El universo completo de status no está documentado -- un valor
        # no anticipado por Phoenix no debe rechazarse a nivel de contrato.
        metadata = _metadata(instrument_status="SomeFutureStatus")
        assert metadata.instrument_status == "SomeFutureStatus"

    def test_contract_type_must_be_str(self):
        with pytest.raises(TypeError, match="contract_type must be str"):
            _metadata(contract_type=1)

    def test_contract_type_must_not_be_empty(self):
        with pytest.raises(ValueError, match="contract_type must not be empty"):
            _metadata(contract_type="")

    # ── tick_size / min_price / max_price ───────────────────────────────

    def test_tick_size_must_be_decimal(self):
        with pytest.raises(TypeError, match="tick_size must be Decimal"):
            _metadata(tick_size=0.1)

    def test_tick_size_rejects_nan(self):
        with pytest.raises(ValueError, match="tick_size must be finite"):
            _metadata(tick_size=Decimal("nan"))

    def test_tick_size_must_be_positive(self):
        with pytest.raises(ValueError, match="tick_size must be > 0"):
            _metadata(tick_size=Decimal("0"))

    def test_tick_size_rejects_negative(self):
        with pytest.raises(ValueError, match="tick_size must be > 0"):
            _metadata(tick_size=Decimal("-0.1"))

    def test_min_price_must_be_decimal(self):
        with pytest.raises(TypeError, match="min_price must be Decimal"):
            _metadata(min_price=0.1)

    def test_min_price_zero_is_valid(self):
        metadata = _metadata(min_price=Decimal("0"))
        assert metadata.min_price == Decimal("0")

    def test_min_price_rejects_negative(self):
        with pytest.raises(ValueError, match="min_price must be >= 0"):
            _metadata(min_price=Decimal("-1"))

    def test_min_price_rejects_nan(self):
        with pytest.raises(ValueError, match="min_price must be finite"):
            _metadata(min_price=Decimal("nan"))

    def test_max_price_must_be_decimal(self):
        with pytest.raises(TypeError, match="max_price must be Decimal"):
            _metadata(max_price=100.0)

    def test_max_price_zero_is_valid(self):
        # Sin invariante cruzada con min_price -- ver comentario en el
        # contrato: Bybit no documenta max_price > min_price garantizado.
        metadata = _metadata(min_price=Decimal("0"), max_price=Decimal("0"))
        assert metadata.max_price == Decimal("0")

    def test_max_price_rejects_negative(self):
        with pytest.raises(ValueError, match="max_price must be >= 0"):
            _metadata(max_price=Decimal("-1"))

    def test_max_price_not_required_to_exceed_min_price(self):
        # Deliberado: no se inventa una invariante cruzada no documentada.
        metadata = _metadata(min_price=Decimal("100"), max_price=Decimal("50"))
        assert metadata.min_price == Decimal("100")
        assert metadata.max_price == Decimal("50")

    # ── qty_step / min_order_qty / max_order_qty ────────────────────────

    def test_qty_step_must_be_decimal(self):
        with pytest.raises(TypeError, match="qty_step must be Decimal"):
            _metadata(qty_step=0.001)

    def test_qty_step_must_be_positive(self):
        with pytest.raises(ValueError, match="qty_step must be > 0"):
            _metadata(qty_step=Decimal("0"))

    def test_qty_step_rejects_negative(self):
        with pytest.raises(ValueError, match="qty_step must be > 0"):
            _metadata(qty_step=Decimal("-0.001"))

    def test_min_order_qty_must_be_decimal(self):
        with pytest.raises(TypeError, match="min_order_qty must be Decimal"):
            _metadata(min_order_qty=0.001)

    def test_min_order_qty_must_be_positive(self):
        with pytest.raises(ValueError, match="min_order_qty must be > 0"):
            _metadata(min_order_qty=Decimal("0"))

    def test_max_order_qty_must_be_decimal(self):
        with pytest.raises(TypeError, match="max_order_qty must be Decimal"):
            _metadata(max_order_qty=1190.0)

    def test_max_order_qty_zero_is_valid(self):
        # Un maximo de 0 podria representar legitimamente trading de limite
        # suspendido -- no se asume que nunca ocurre.
        metadata = _metadata(max_order_qty=Decimal("0"))
        assert metadata.max_order_qty == Decimal("0")

    def test_max_order_qty_rejects_negative(self):
        with pytest.raises(ValueError, match="max_order_qty must be >= 0"):
            _metadata(max_order_qty=Decimal("-1"))

    # ── max_market_order_qty (accesorio) ────────────────────────────────

    def test_max_market_order_qty_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionInstrumentMetadata)
                     if f.name == "max_market_order_qty")
        assert field.default is None

    def test_max_market_order_qty_none_is_valid(self):
        metadata = _metadata(max_market_order_qty=None)
        assert metadata.max_market_order_qty is None

    def test_max_market_order_qty_must_be_decimal_when_present(self):
        with pytest.raises(TypeError, match="max_market_order_qty must be Decimal or None"):
            _metadata(max_market_order_qty=500.0)

    def test_max_market_order_qty_zero_is_valid(self):
        metadata = _metadata(max_market_order_qty=Decimal("0"))
        assert metadata.max_market_order_qty == Decimal("0")

    def test_max_market_order_qty_rejects_negative(self):
        with pytest.raises(ValueError, match="max_market_order_qty must be >= 0"):
            _metadata(max_market_order_qty=Decimal("-1"))

    def test_max_market_order_qty_distinct_from_max_order_qty(self):
        # Confirmado por el ejemplo oficial de Bybit -- ambos valores
        # difieren para el mismo instrumento.
        metadata = _metadata(max_order_qty=Decimal("1190.000"), max_market_order_qty=Decimal("500.000"))
        assert metadata.max_order_qty != metadata.max_market_order_qty

    # ── min_notional_value (accesorio) ──────────────────────────────────

    def test_min_notional_value_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionInstrumentMetadata)
                     if f.name == "min_notional_value")
        assert field.default is None

    def test_min_notional_value_none_is_valid(self):
        metadata = _metadata(min_notional_value=None)
        assert metadata.min_notional_value is None

    def test_min_notional_value_must_be_decimal_when_present(self):
        with pytest.raises(TypeError, match="min_notional_value must be Decimal or None"):
            _metadata(min_notional_value=5.0)

    def test_min_notional_value_zero_is_valid(self):
        metadata = _metadata(min_notional_value=Decimal("0"))
        assert metadata.min_notional_value == Decimal("0")

    def test_min_notional_value_rejects_negative(self):
        with pytest.raises(ValueError, match="min_notional_value must be >= 0"):
            _metadata(min_notional_value=Decimal("-1"))

    def test_min_notional_value_distinct_concept_from_min_order_qty(self):
        # min_notional_value es price*qty, no una cantidad de contratos --
        # el contrato no los conflacio ni impone relacion entre ambos.
        metadata = _metadata(min_order_qty=Decimal("0.001"), min_notional_value=Decimal("5"))
        assert metadata.min_order_qty != metadata.min_notional_value

    # ── leverage filter (accesorio, metadata no operativa) ──────────────

    def test_min_leverage_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionInstrumentMetadata) if f.name == "min_leverage")
        assert field.default is None

    def test_min_leverage_none_is_valid(self):
        metadata = _metadata(min_leverage=None)
        assert metadata.min_leverage is None

    def test_min_leverage_must_be_decimal_when_present(self):
        with pytest.raises(TypeError, match="min_leverage must be Decimal or None"):
            _metadata(min_leverage=1.0)

    def test_min_leverage_must_be_positive_when_present(self):
        with pytest.raises(ValueError, match="min_leverage must be > 0"):
            _metadata(min_leverage=Decimal("0"))

    def test_max_leverage_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionInstrumentMetadata) if f.name == "max_leverage")
        assert field.default is None

    def test_max_leverage_none_is_valid(self):
        metadata = _metadata(max_leverage=None)
        assert metadata.max_leverage is None

    def test_max_leverage_must_be_positive_when_present(self):
        with pytest.raises(ValueError, match="max_leverage must be > 0"):
            _metadata(max_leverage=Decimal("0"))

    def test_leverage_step_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionInstrumentMetadata) if f.name == "leverage_step")
        assert field.default is None

    def test_leverage_step_none_is_valid(self):
        metadata = _metadata(leverage_step=None)
        assert metadata.leverage_step is None

    def test_leverage_step_must_be_positive_when_present(self):
        with pytest.raises(ValueError, match="leverage_step must be > 0"):
            _metadata(leverage_step=Decimal("0"))

    def test_max_leverage_not_required_to_exceed_min_leverage(self):
        # Deliberado: sin invariante cruzada no confirmada.
        metadata = _metadata(min_leverage=Decimal("50"), max_leverage=Decimal("10"))
        assert metadata.min_leverage == Decimal("50")
        assert metadata.max_leverage == Decimal("10")

    # ── server_time_ms ───────────────────────────────────────────────────

    def test_server_time_ms_must_be_int(self):
        with pytest.raises(TypeError, match="server_time_ms must be int"):
            _metadata(server_time_ms=1.5)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError, match="server_time_ms must be >= 0"):
            _metadata(server_time_ms=-1)

    def test_server_time_ms_always_required_no_default(self):
        with pytest.raises(TypeError):
            ExecutionInstrumentMetadata(
                symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", settlement_asset="USDT",
                instrument_status="Trading", contract_type="LinearPerpetual",
                tick_size=Decimal("0.1"), min_price=Decimal("0.1"), max_price=Decimal("100"),
                qty_step=Decimal("0.1"), min_order_qty=Decimal("0.1"), max_order_qty=Decimal("100"),
            )

    # ── superficie / equality ────────────────────────────────────────────

    def test_repr_does_not_crash(self):
        text = repr(_metadata())
        assert "BTCUSDT" in text

    def test_equality_by_value(self):
        assert _metadata() == _metadata()

    def test_inequality_on_different_symbol(self):
        assert _metadata(symbol="BTCUSDT") != _metadata(symbol="ETHUSDT")


class TestPurityByAst:
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
        import execution_gateway.instrument_metadata_contracts as module
        imports = self._module_imports(module)
        violations = [i for i in imports if any(f in i.lower() for f in self._FORBIDDEN_SUBSTRINGS)]
        assert violations == []

    def test_contracts_module_imports_are_stdlib_only(self):
        import execution_gateway.instrument_metadata_contracts as module
        imports = self._module_imports(module)
        assert set(imports) == {"dataclasses", "decimal"}

    def test_reader_protocol_module_has_no_forbidden_imports(self):
        import execution_gateway.instrument_metadata_reader as module
        imports = self._module_imports(module)
        violations = [i for i in imports if any(f in i.lower() for f in self._FORBIDDEN_SUBSTRINGS)]
        assert violations == []

    def test_reader_protocol_module_only_imports_typing_and_own_contract(self):
        import execution_gateway.instrument_metadata_reader as module
        imports = self._module_imports(module)
        assert set(imports) == {"typing", "execution_gateway.instrument_metadata_contracts"}
