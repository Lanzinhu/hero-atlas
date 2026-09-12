"""Controle: do erro de atitude ao comando de cada propulsor.

Duas camadas, deliberadamente separadas:

    erro -> wrench desejado   (controlador, :mod:`attitude`)
    wrench -> comandos        (alocador, :mod:`allocator`)

O alocador **nao** promete empuxo instantaneo. Ver ADR-003.
"""
