---
title: "Channel id"
status: proposed
authors:
  - "@paluh"
  - "@waalge"
date: 2024-10-24
tags:
  - l1
---

## Context

The [minimal lifecycle](./minimal-lifecycle.md) implies some state of a channel
is kept on-chain. The assumption is that a channel is represented on the L1 by a
single utxo.

A channel must be identifiable for:

- off-chain:
  - participants following own channels' state eg watch for a close step
  - for participants with different levels of L1 connectivity, from all history
    to only via Mithril
- on-chain:
  - finding continuing input
  - verifying that a cheque corresponds to the given channel
  - interacting with another script

A utxo has four attributes: address, value, datum, reference script. The latter
two are optional.

With regards to the address, the payment credential of the address must be a
script enforcing the CL logic. The staking credentials are of concern only when
the currency is Ada. We leave this as an open question for now.

For the channel utxo, the reference script must be `None`. Although this is a
decision - it seems self evident that this should be the case.

We also take it as assumed that the datum is used and is inline.

The question is

> how should channels be identified

## Decision

A channel is identified by its thread token.

### Overview

The thread token is an NFT. The script is the same as the spending script,
invoked with a different purpose. Thus the script can determine its own hash
from either a policy id or payment credentials.

The token name is:

```rs
let name = "⚡" + cid
```

where

- `cid = take 20 $ blake2b_256 $ concat seed idx`
- `seed` is the oref of some input spent in the mint.
- `idx` is the relative output index the minting tx outputs the thread token.

The thread token never leaks from the thread, ie channel utxo. It is burned in
an unstaging (ie terminating) step.

Within a single transaction, there is at most one `seed`. All thread tokens are
output in consecutive utxos, making it simpler and cheaper to handle the `idx`.

Note that the mint value will list the tokens 'out of order' relative to the
outputs.

### Rationale

The thread token is a well understood design pattern. It seems to be favoured by
(some) auditors on the grounds that it is easier to reason about that
alternatives.

TODO: rework the below.

- It is hard to imagine direct incentiviced attack on a single channel when both
  parties know and track the exact state of the channel by performing L1
  queries.
- It is probably more probable that some form of incentivized attack can be
  performed when we imagine payment operators - some security attacks can depend
  on confusion and weakness of the sofware behind it.

#### Pros

- Simplify off-chain validity checks - single script hash determines `Value`,
  `Datum` and `Script` consistency. This can have an minimal impact on indexers
  performance.

- Removes ambiguity - uniqueness is a guaranteed invariant. This simplifies not
  only indexers but other software as well.

- Simplify on-chain contract preservation checks (continuing UTxO
  identification) - useful in both singleton and batch mode.

#### Cons

- Makes Hydra integration harder. Specifically propogating a channel from the L2
  to the L1. per channel then we could:
  - Mint a unique one based on randomness commitments (both parties provide
    signed hashes of "random" numbers)
  - We compute the final value from xoring the preimiges
  - We store the commitments in the state
  - We use the commitments to recompute the token when performing the minting
    during the settlement of the channel on the L1 in the case when Hydra head
    is closed before the CL channel is closed.

## Discussion, Counter and Comments

### Considered Alternatives

#### No cid

The channel is associated with the initial UTxO and the client folds the
contract thread.

In order to operate safely it requires full access an indexer which provides all
the intermediate transactions.

Advantages:

- trivial hydra compat (no token)

Disadvantages:

- Off-chain tracking is much more complicated/ expensive since it requires
  history, rather than just tip.
- Shifts complexity onto cheques and cheque handling
- Depending on other design decisions, it has implications for safety on key
  reuse.

#### cid via datum

The `cid` is part of the datum. All steps require the persistence of at least
some of the datum. The `cid` would be another field which is checked to persist.

Advantages:

- trivial hydra compat (no token)

Disadvantages:

- Allows channel spoofing
- Makes indexing potentially more fiddly since indexers generally support
  inspecting the value of utxo more straightforwardly than parsing a custom
  datum and pulling out a value.

A version of this bases the `cid` on the partners keys.  
The channel l1 already requires recording the pubkeys of the partners. These
must be stored in the datum. These could be used, eg concatenated or
concatenated and hashed, to form a `cid`. This shares the advantages and
disadvantages above. It requires one fewer field being stored in the datum, but
at the cost of slightly more laborious pattern checking, and implications for
key reuse.

#### Alternative id generators

A mildly cheaper version requires making only one hash:
`cid' = push idx digest`, where

- `digest = (take 20 $ blake2b_224 seed)`
- We'd limit `idx < 256`

An advantage is that the tokens are in the order they are output. A drawback is
that the channel ids will differ only by a single byte.

### Comments

#### Hydra compat

TODO

#### Mithril compat

Current Mithril API:

- The last transaction body required from untrusted source.
  - Query to the existing Mithril transaction API (by hash) proves validity of
    that transaction and possibly past state of the channel.cardano
  - Combined with query about the recent certified block it can actually give
    short lived off-chain guarantees about the channel state.
- Light wallet Mithril API (the latest Mithril design discussion:
  https://github.com/input-output-hk/mithril/discussions/1273):
  - Given known script address we can query the Mithril for the UTxOs at address
    which should be
  - The above query can be really inefficient and return massive results (UTxOs
    for all the open channels). We can narrow the query by using unique staking
    part per channel.

#### Other script compat

We don't yet know what this might be.

As a best guess: Its easier for other script and tool devs to reason about and
use a thread token rather than the alt suggestions.

## Consequences

# FIXME

## Do we need it?

## Self hash discovery

- Spending validator self hash discovery is costly `O(n)` where `n` is in the
  number of inputs.

- We discover self hash by "trusting" the thread token and avoid the cost.

- This is "unsafe" on the chain but safe from off-chain perspective because we
  ignore all non valid tokens right away.

- In the case of minting and batching (rewarding) we have `O(1)` self hash
  discovery.

## Pros

- Self preservation check We can use this to discover the self hash which will
  be used for self preservation cheqk

- Off-chain identification of only valid channels is trivial.

- Simplifies off-chain implementations

- Given the above presence of such a token uniquely identifies **only** valid
  channel and it can not be forged.
