---
title: "Channel identification"
status: proposed
authors: "@paluh"
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

The thread token is an NFT. The token's script is the same as that of the
payment credentials. The token name is

```rs
let name = "⚡" + cid
```

where

- `cid = blake2b_224 seed`
- `seed` is the oref of some input spent in the mint.

The thread token never leaks from the thread and that it is burned in an
unstaging step.

### Rationale

The thread token is relatively old design pattern. It seems to be favoured by
(some) auditors, on the grounds that it is easier to reason about that
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

- Removes ambiguity - uniquness is a guaranteed invariant. This simplifies not
  only indexers but other software as well.

- Simplify on-chain contract preservation checks (continuing UTxO
  identification) - useful in both singleton and batch mode.

#### Cons

- Makes Hydra integration a bit harder. If we require presence of a unique token
  per channel then we could:
  - Mint a unique one based on randomness commitments (both parties provide
    signed hashes of "random" numbers)
  - We compute the final value from xoring the preimiges
  - We store the commitmets in the state
  - We use the commitments to recompute the token when performing the minting
    during the settlment of the channel on the L1 in the case when Hydra head is
    closed before the CL channel is closed.

## Discussion, Counter and Comments

### Considered Alternatives

#### No cid

Channel is associated with the initial UTxO and the client folds the contract
thread.

In order to operate safely:

- requires full access an indexer which provides all the intermediate
  transactions and requires querying Mithril aggregator for all the
  transactions, OR
- requires a trusted indexer so cardano node as well.

Advantages:

- trivial hydra compat (no token)

Disadvantages:

- Off-chain tracking is much more complicated/ expensive: Requires history,
  rather than just tip.
- Seems to shift complexity onto cheques and cheque handling
- Depending on other design decisions, has implications for key reuse

#### cid via pubkeys

The channel l1 already requires recording the pubkeys of the partners. These
must be stored in the datum. These could be used, eg concatenated or
concatenated and hashed, to form a `cid`.

Advantages:

- trivial hydra compat (no token)

Disadvantages:

- Allows channel spoofing
- A pair of keys can only be used safely in a single instance

#### cid via datum

The `cid` is part of the datum. All steps require the persistence of at least
some of the datum. The `cid` would be another field which is checked to persist.

Advantages:

- trivial hydra compat (no token)

Disadvantages:

- Allows channel spoofing

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
