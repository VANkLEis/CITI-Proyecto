"""Limpieza de texto para PlantUML: repara mojibake y pliega a ASCII.

Los diagramas se generan con texto ASCII para que el render sea idéntico en
cualquier JVM/Windows, sin depender de la codificación de la consola.
"""

MOJIBAKE = {
    "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ",
    "ÃÁ": "Á", "Ã‰": "É", "ÃÍ": "Í", "Ã“": "Ó", "Ãš": "Ú", "Ã‘": "Ñ",
    "Â·": "·", "Â¿": "¿", "Â¡": "¡", "Âº": "º", "Âª": "ª",
    "â€“": "–", "â€”": "—", "â€œ": "“", "â€\x9d": "”", "â€™": "’",
    "â†’": "→", "â€¦": "…", "â‚¬": "€",
}

FOLD = str.maketrans({
    "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
    "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ñ": "N",
    "ü": "u", "Ü": "U", "·": "-", "¿": "?", "¡": "!",
    "–": "-", "—": "-", "“": '"', "”": '"', "’": "'", "…": "...",
    "→": "->", "€": "EUR", "º": "o", "ª": "a",
})


def clean_line(line: str) -> str:
    for bad, good in MOJIBAKE.items():
        line = line.replace(bad, good)
    return line.translate(FOLD)


def clean(text: str) -> str:
    return "\n".join(clean_line(line) for line in text.splitlines())
