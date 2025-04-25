import string


def get_fstring_kwords(template: str) -> list[str]:
    formatter = string.Formatter()
    return [fname for _, fname, _, _ in formatter.parse(template) if fname]
