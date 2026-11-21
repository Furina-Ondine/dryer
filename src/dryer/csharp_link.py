"""Load the shared C# frontend only for C# source files."""


class CSharpDependencyError(ImportError):
    """The installed Crapper does not provide the shared C# frontend."""


class CSharpSyntaxError(SyntaxError):
    """The C# parser could not extract complete syntax."""


_MISSING = (
    "C# analysis requires Crapper with C# support. "
    "Install the companion Crapper checkout in Dryer's Python environment."
)


def _discovery():
    try:
        from crapper import discover
    except ImportError as error:
        raise CSharpDependencyError(_MISSING) from error
    if not hasattr(discover, "is_production_source"):
        raise CSharpDependencyError(_MISSING)
    return discover


def language_of(path):
    return _discovery().language_of(path)


def is_production_source(path):
    return _discovery().is_production_source(path)


def units_in_source(source, path):
    try:
        from crapper.languages.csharp import units_in_source as read
    except ImportError as error:
        raise CSharpDependencyError(_MISSING) from error
    try:
        return read(source, path)
    except SyntaxError as error:
        raise CSharpSyntaxError(str(error)) from error
