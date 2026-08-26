# v0.5.1 save compatibility fixes

## Item flag format

Static analysis of the v5.10 application confirms that the 12-digit item flag is formatted as:

```text
BBBB-UU-TT-GGGG
```

- `BBBB`: base item ID
- `UU`: super-rare/UQ ID
- `TT`: ordinary title ID
- `GGGG`: gem/additional ID (`0000` or gem ID)

v0.5.0 incorrectly treated the suffix as the super-rare field. v0.5.1 detects and repairs that legacy output.

Regression examples from the supplied before/after saves:

```text
853100090003 -> 853123090000
650100090031 -> 650151090000
401300090069 -> 401389090000
```

## sysAPov / addon budget

The application does not persist `adonPoint_max` as a standalone save value. It derives the budget from unlock flags before saving and records `sysAPov` when allocated points exceed that derived budget.

Static analysis of v5.10 confirms:

```text
base                         3
Guild2.adonPow1..10          +1 each
Guild2.adonBisiness1         +5
```

Current game documentation raises purchasable addon points by five, yielding the current maximum of 23 points. v0.5.1 therefore models the current save-compatible unlock set as `Guild2.adonPow1..15` plus `Guild2.adonBisiness1`, while retaining the distinction between values confirmed directly in v5.10 and the five later purchase flags supported by current-game documentation.

The editor can add the missing current unlock flags to raise the derived budget to 23. If `sysAPov` is already present, it is removed only after the allocation fits the newly derived budget; unrelated `sys*` flags are preserved.

## Rabbit value

Real saves may encode `rabbit` as a finite floating-point value very close to an integer. Validation now checks the confirmed range `0..999` rather than requiring an exact JavaScript integer.
