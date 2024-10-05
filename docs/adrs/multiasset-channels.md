---
title: "Support monoasset channels, not full multiasset"
status: proposed
authors: "@waalge"
date: 2024-09-02
tags:
  - multiasset
---

## Context

The Cardano ledger supports multiassets.

Lightning channels could also support multiassets.

Benefits:

- TODO

Costs:

- More complexity to handle: Partial ordering instead of total ordering;
  `Value` datatype is much more expensive to store and manipulate over simply `Int`.
- Routing becomes much more of headache.

## Decision

Lightning channels support monoassets only.
That is, non ada assets are supported but only one asset class can be used in a given channel.

## Decent, counter, and comments

TODO

## Consequences

All txs must check the continued value explicitly for token inclusion.
This should be the case anyway to catch token spamming.

### Infer from value

There current design assumes that the underlying asset is ada.
Moving to monoasset, we can pattern match on flattened value.
Assuming a state token is used, this will look like:

```aiken
when (own_value |> value.flatten()) is {
  [(_,_,amt), (own_pid_, state_tn, 1)] -> { ... } // Ada case.
  [_, (own_pid_, state_tn, 1), (pid, tn, amt)] -> { ... } // Non ada case.
  _ -> fail "absurd"
}
```

Note in reality we must also handle case that `pid < own_pid_`

In the non-ada case, the ada involved is assumed to be only the amount required to adhere to min ada ledger rules.
It is not considered in part of the constraints.

However this does impose the additional constraint that the continuing `amt` cannot drop below `1`.
This constraint can be assumed in the ada case due to the aforementioned min ada ledger rules.

### Infer from datum

Alternative implementation could specify the asset class in the `FixDat` part of the datum.
