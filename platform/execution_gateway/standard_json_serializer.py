import json


class StandardJsonSerializer:
    def dumps(self, value: object) -> str:
        return json.dumps(value)

    def loads(self, value: str) -> object:
        return json.loads(value)
