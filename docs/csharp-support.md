# C# support development evidence

The public language key is `csharp`; the parser grammar is `c_sharp`. Existing
`Entry`, duplicate report and EDN formats remain compatible.

## 2026-11-14: executable C# members

1. Read the extraction, discovery, normalization and CLI paths and the ub-mode
   skill before choosing the extension points. Inspected the installed C# parser
   with real constructor/operator/accessor/expression-body samples.
2. Added C# behavior tests first. The initial run failed all 15 cases because
   `.cs` was unknown and C# extraction returned no forms.
3. Added `.cs` discovery and executable-member extraction. Local functions and
   lambdas remain inside their member; declarations without executable bodies
   contribute no candidates. Added invocation, generic-call and member-access
   normalization while preserving call names and constructed type names.
4. Added .NET build/generated-file exclusions and a real CLI report/metrics test.
   The full regression suite passed: **104 tests**.
5. Installed `coverage` into the existing repository-local virtual environment
   for the quality gate. A first custom coverage command wrote LCOV outside the
   tool's discovery location; reran Crapper with its standard coverage command.
6. Crapper passed for all three modified analysis modules: maximum CRAP **8.2**;
   `_csharp_nodes` has 100% line coverage and CRAP **4.0**. Dryer reported no
   duplicate pair at threshold **0.8** in those modules.
7. Ran Mutator against all three modified analysis modules, with its standard
   Python runner and `--no-coverage --mutate-all --max-workers 4`: **106 killed,
   0 survived, 0 uncovered**. This executes every supported mutation regardless
   of coverage filtering. Mutator has no sites for the language/node-type
   lookup tables, whose behavior is checked by the C# tests.

Reproduce from the repository root with the local companion repositories:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
..\crapper\crapper.ps1 --root . --threshold 9.999 src/dryer/discover.py src/dryer/extract.py src/dryer/astnorm.py
.\dryer.ps1 --root . --threshold 0.8 src/dryer/discover.py src/dryer/extract.py src/dryer/astnorm.py
..\mutator\mutator.ps1 --root . --no-coverage --mutate-all --max-workers 4 src/dryer/discover.py src/dryer/extract.py src/dryer/astnorm.py
```
