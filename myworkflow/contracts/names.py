"""Canonical Python interface names derived from stable contract IDs."""


def class_name(identity):
    return "".join(part.title() for part in identity.replace(".", "-").split("-"))
