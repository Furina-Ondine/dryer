# C# support development evidence

C# uses Crapper's shared SDK Roslyn frontend. Dryer consumes its executable
units and native syntax roles through the existing extraction registry,
normalizer, fingerprints, Jaccard comparison and report formats. It has no
second C# parser or private executable-member walker.

## Ordered development

1. Added failing discovery/member tests, then registered `.cs` and executable
   bodies. Local functions and lambdas belong to their enclosing member;
   top-level statements are one ordered candidate.
2. Pinned operation and constructed-type names, conditional/generic calls,
   accessor spans and generated/test-file discovery. Language registration
   follows the existing reader extension point.
3. Reproduced legal ref-return syntax being rejected and malformed syntax being
   accepted by the previous parser. Replaced the C# reader with shared compiler
   documents and units. Unicode/CRLF ranges and diagnostics are behavior tests.
4. A Java anonymous class exposed discarded trailing call syntax. The common
   call job list now retains receivers, arguments and trailing children once.
   Compiler identifier tokens also survive path traversal so generic callee
   names remain significant.
5. Replaced the CLI option ladder with value/switch tables after its CRAP gate
   failed. Kept argument, report and exit behavior covered.
6. Tested missing Crapper imports in an isolated process and in the current
   process, including a broken installed package shadowing a valid sibling.
   CI supplies the matching same-owner Crapper checkout and .NET SDK.

## Verification

The full regression suite passes 123 tests. All modified production functions
have CRAP below 10 (maximum 9). Dryer reports no duplicate candidates at 0.8
across the touched production modules.

Early all-killed mutation runs were invalidated: the unchanged private worker
could fail because of missing launcher/dependency setup. They are not evidence.
The corrected control first proves an unchanged worker passes, then runs the
same non-launcher tests for each supported mutation. Full launcher integration
remains in the complete regression suite.

The verified changed-function results are 77 killed and five surviving
head-flag mutations in `_call_jobs`. Those five affect callee mode, which ignores
that flag, or argument/type-argument/trailing composite wrappers, which reset it
before visiting their children. They are equivalent for the supported call
shapes. Separate Java and compiler-AST behavior tests pin child order, call
names and trailing syntax. Three earlier non-equivalent survivors in import
precedence and single/multiple-unit assembly were killed by added behavior tests.

Real project runs use Metaheuristics.NET, v2rayN, runtime's CommandLine module,
Avalonia.Base, PowerShell's engine and Files.Shared. The workspace validation
log distinguishes full syntax audits from selected-module duplicate analysis.

## Reproduce

From sibling checkouts containing matching Crapper and Mutator versions:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
..\crapper\crapper.ps1 --root . --threshold 9.999 --use-existing-coverage src/dryer
.\dryer.ps1 --root . --threshold 0.8 src/dryer
```

Mutation commands must have the matching compiler dependency and a passing
unchanged worker. Install or merge Crapper's frontend before this release.
