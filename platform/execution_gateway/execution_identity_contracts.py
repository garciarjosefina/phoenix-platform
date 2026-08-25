from dataclasses import dataclass

# Identidad canónica de orden del bounded context de ejecución.
#
# El formato es "ord_" + uuid4().hex = 4 + 32 = 36 caracteres exactos.
# Esa longitud no es estética: es la restricción externa de `orderLinkId`
# de Bybit (máximo 36 caracteres; charset documentado como "combinations
# of numbers, letters (upper and lower cases), dashes, and underscores";
# unicidad obligatoria -- ver ADR-008). La identidad se diseña compatible
# DE ORIGEN con esa frontera, en vez de adaptarse/truncarse al cruzarla.
#
# `uuid4().hex` produce 32 caracteres hexadecimales en MINÚSCULA y
# conserva íntegros los 122 bits aleatorios efectivos de UUID4 -- nunca
# se recorta, ni se eliminan caracteres, ni se reempaqueta. Truncar
# destruiría la garantía probabilística sin declararlo.
_EXECUTION_ORDER_ID_PREFIX = "ord_"
_EXECUTION_ORDER_ID_HEX_LEN = 32
_EXECUTION_ORDER_ID_LEN = len(_EXECUTION_ORDER_ID_PREFIX) + _EXECUTION_ORDER_ID_HEX_LEN
_LOWERCASE_HEX = frozenset("0123456789abcdef")


def _require_non_empty_str(value, *, field: str) -> None:
    # Identidad de string literal y exacta -- sin strip/upper/lower/casefold,
    # igual que en el resto del bounded context (ADR-005, Decisión 3). Un
    # valor con espacios alrededor NO se normaliza: si no es whitespace-only,
    # esos espacios forman parte de la identidad.
    if not isinstance(value, str):
        raise TypeError(f"{field} must be str, got: {type(value).__name__}")
    if not value or value.isspace():
        raise ValueError(f"{field} must not be empty or whitespace-only")


@dataclass(frozen=True)
class ExecutionAccountId:
    """Identidad INTERNA y opaca de Phoenix para una cuenta de ejecución.

    NO es una credencial: `api_key`/`api_secret`, cualquier huella de un
    secreto, el nombre de una variable de entorno o una `base_url` están
    explícitamente prohibidos como identidad de cuenta (ADR-008, D3) --
    las credenciales autentican, no identifican.

    NO es un environment: Demo/Mainnet es una dimensión distinta y vive
    en ExchangeAccountIdentity, nunca aquí (ADR-008, D4).

    NO se genera sola: este contrato RECIBE una identidad acuñada por una
    capa autorizada. Deliberadamente no existe todavía un formato textual
    congelado ni un generador oficial para esta identidad, porque no
    existe todavía la autoridad que la acuñaría (el futuro Account
    Registry). El contrato puede representar cualquier identidad recibida
    -- p.ej. ExecutionAccountId(value="PHX-ACCOUNT-001") es válido como
    valor recibido, sin que eso congele ese formato.

    Su relación con la identidad remota observable (ExchangeAccountIdentity)
    será responsabilidad de ese Account Registry futuro; hoy NO existe
    binding alguno entre ambas.
    """

    value: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.value, field="value")


@dataclass(frozen=True)
class ExchangeAccountIdentity:
    """Identidad OBSERVABLE de una cuenta remota, tal como el exchange la
    reporta. Es vocabulario de dominio, no un binding persistido.

    Las tres dimensiones son identidad, no metadata: el mismo
    `remote_user_id` puede existir en environments distintos (Demo y
    Mainnet son sistemas Bybit separados) y, en el futuro, en exchanges
    distintos. Por eso la identidad es la tupla completa y nunca
    `remote_user_id` a secas (ADR-008, D4).

    `remote_user_id` es `str` y no `int` deliberadamente: Bybit expone
    tanto `userID` (entero) como `userIDInt64` (string), y el resto del
    bounded context ya preserva identificadores remotos como strings
    exactos (ver `exchange_order_id`). Se preserva literalmente lo que el
    exchange reporte, sin reinterpretarlo numéricamente.

    Deliberadamente SIN `parent_uid`/`is_master`: describen la relación
    cuenta principal/subcuenta, no la identidad de esta cuenta. Son
    metadata de jerarquía y se modelarán, si hace falta, donde
    corresponda (ADR-008).

    Deliberadamente SIN credenciales de ningún tipo.

    Hoy NINGÚN componente de producción construye este contrato: la
    primitiva que consultaría `GET /v5/user/query-api` para observar esta
    identidad no existe todavía (ADR-008, OPEN QUESTIONS 4).
    """

    exchange: str
    environment: str
    remote_user_id: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.exchange, field="exchange")
        _require_non_empty_str(self.environment, field="environment")
        _require_non_empty_str(self.remote_user_id, field="remote_user_id")


@dataclass(frozen=True)
class ExecutionOrderId:
    """Identidad Phoenix de una orden del bounded context de ejecución.

    Distinta por definición del `exchange_order_id` (el `orderId` que
    asigna Bybit): esta identidad la acuña Phoenix ANTES de que la orden
    exista remotamente, y viaja al exchange como `orderLinkId`. El
    `exchange_order_id` nunca la sustituye ni actúa como fallback
    (ADR-005, Decisión 4).

    Formato canónico ESTRICTO: "ord_" + exactamente 32 caracteres
    hexadecimales en minúscula (36 en total). El contrato valida el
    formato oficial completo, no una compatibilidad genérica con la
    frontera: la decisión arquitectónica congeló este formato como LA
    identidad canónica del bounded context (ADR-008), así que un string
    que sólo "parece" compatible -- corto, con charset válido, pero sin
    el formato -- no es una identidad de ejecución Phoenix y se rechaza.
    Un `orderLinkId` remoto que no cumpla este formato simplemente no es
    una orden Phoenix, lo cual es una afirmación más fuerte y más útil
    que "cabe en 36 caracteres".

    Minúscula estricta y no normalización: `uuid4().hex` produce
    minúsculas, y la documentación de Bybit no se pronuncia sobre
    case-sensitivity de `orderLinkId`. Aceptar mayúsculas crearía dos
    strings distintos que representarían "la misma" orden sin que exista
    evidencia de que el exchange los trate como iguales -- exactamente la
    ambigüedad de identidad que este proyecto rechaza. Se acepta sólo lo
    que el generador oficial produce.

    NO embebe `bot_id`, `account_id` ni `strategy_id`: la atribución por
    bot vive en el futuro Ledger como dimensión separada, nunca dentro
    del texto de la identidad (ADR-008, D5/D6).

    NO se genera sola -- ver `create_execution_order_id`.
    """

    value: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.value, field="value")

        if len(self.value) != _EXECUTION_ORDER_ID_LEN:
            raise ValueError(
                f"value must be exactly {_EXECUTION_ORDER_ID_LEN} characters "
                f"('{_EXECUTION_ORDER_ID_PREFIX}' + {_EXECUTION_ORDER_ID_HEX_LEN} lowercase "
                f"hex digits), got: {len(self.value)}"
            )
        if not self.value.startswith(_EXECUTION_ORDER_ID_PREFIX):
            raise ValueError(
                f"value must start with {_EXECUTION_ORDER_ID_PREFIX!r}, got: {self.value!r}"
            )

        suffix = self.value[len(_EXECUTION_ORDER_ID_PREFIX):]
        if not all(character in _LOWERCASE_HEX for character in suffix):
            raise ValueError(
                f"value must end with {_EXECUTION_ORDER_ID_HEX_LEN} lowercase hex digits, "
                f"got: {self.value!r}"
            )
