import string
import os

def get_fstring_kwords(template: str) -> list[str]:
    formatter = string.Formatter()
    return [fname for _, fname, _, _ in formatter.parse(template) if fname]

def _resolve_env_value(field: str, dotenv: dict) -> str | None:
    for key in [field, field.upper(), field.lower()]:
        if (val := os.getenv(key)) is not None:
            return val
        if (val := dotenv.get(key)) is not None:
            return val
    return None

def load_settings(cls, env_file=".env"):
    dotenv = dotenv_values(env_file)
    values = {
        field: _parse_value(field, _resolve_env_value(field, dotenv))
        for field in cls.model_fields
    }
    return cls(**values)

