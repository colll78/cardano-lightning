---
title: "The sub step"
status: proposed
authors: "@waalge"
date: 2024-10-24
tags:
  - optional
---

## Context

The anticipated usage of CL is that although bidirectionality is utilized, most
channels have _drift_. See elsewhere the categorization of participant behaviour
being one of a 'consumer', a 'merchant', or a 'gateway'. Drift causes the funds
to accrue into one of the two accounts.

The [minimal lifecycle](./minimal-lifecycle.md) of a channel has a significant
shortcoming. Funds are locked until the channel is `Closed` and with reaches
either `Resolved` or `Elapsed` stage.

Furthermore, the minimal lifecycle can only support a limited number of cheques.
This is unpacked to some extend in [minimal state](./minimal-state.md). However,
we've yet to specify exactly what a cheque is and how we prevent double
counting.

## Decision

### Overview

The stages of the minimal lifecycle are unchanged.

There is an additional step `sub` that steps a `Opened` to an `Opened`. The step
is performed by one partner but requires the other partners consent, in the form
of a signed statement.

The minimal state is embelished. The datum is as before with the following
embelishments.

```haskell
data OpenedParams = OpenedParams {
  pk0: Pubkey,
  pk1: Pubkey,
  amt0: Int,
  idx0: Int,
  exc0: Int,
  idx1: Int,
  exc1: Int,
}

data ClosedParams = ClosedParams {
  closer: Pubkey,
  other: Pubkey,
  amtCloser: Int,
  idx: Int,
  exc: Int,
}
```

A cheque has the following form

```haskell
data Cheque
  = NormalCheque Index Amount
  | HtlcCheque Index Amount Timestamp Lock
```

For now we'll ignore locked cheques although there is no significant
modification to accommodate it.

### Rationale

We repeat the same exercise as in minimal state, pointing out the divergences.

#### Steps

##### Open

As before. The datum has `OpenParams ownKey otherKey 0 0 [] 0 []`.

##### Add

As before. The new datum fields are unchanged

##### Close

As before. Note that a cheque must have a valid index with respect to the fields
(`idx*`, `exc*`) corresponding to the `closer`. That is, the list of cheques
index must:

- The list is strictly monotonically increasing in cheque index.
- Either the cheque index is in `exc*` or `> idx*`.

The fields corresponding the `other` account are unchanged when included in the
continuing datum.

TODO: Make explicit 'if `closer == ownKey` then `idx = idx0`...' _etc_ say.

##### Resolve

As before. Same observation regarding valid cheque indexes.

##### Terminating

No change.

##### Sub

On a `sub`:

- The tx is signed by precisely one of the partners, `subber`.
- The `squash` message is signed by the other partner.
- The `squash.oref` is the current oref.
- The continuing funds is at least `squash.total`,
- The continuing datum is `squash.datum`.

Both partners consent to a `sub`: one by signing a `squash`, and the other by
submitting the tx. If either partner is unhappy, they will not provide consent.

After the squash is signed, but before the `sub` is on-chain and finalized, no
partners funds are at risk and the channel can continue operating. That is, so
long as:

- The partners proceed using cheques with indices greater than those in the
  squash.
- In the case the `sub` fails, they are still able to `close` and/ or `resolve`
  all cheques yet accounted for (cf minimal state on tx limits).

The `squash` introduces an additional requirement that the handling of cheques
is paused briefly. Without a `sub`, cheques with different indices can be
handled in parallel. The request by the `subber` to the `squasher` to sign the
`squash` may occur while the `squasher` was sending additional `cheques` - their
two states are out of sync. Both partners have the opportunity to ensure all
cheques are accounted for.

There are more than one possible valid squashes. It is up to the partners to
decide which `squash` is valid. For example, suppose one cheque index has been
isolated to a separate process, or belongs to a locked cheque which has been
issued, not yet resolved but not yet deemed concerning. These indices can be
included in the exclusion list `exc`, or the `idx` could not be incremented.

If the `subber` remains unhappy with the `squash` returned, they can perform a
`close`.

Either partner can invalidate a `squash` if they choose. The `squash` is only
valid from the given state/ utxo. Either partner can invalidate the `squash` by
using an `add` step, a `close` step or performing a `sub` step with a different
`squash`. If the other partner is unhappy, they can perform a `close`.

## Discussion, Counter and Comments

### Comments

The `sub` step allows a channel to remain open essentially indefinitely.

It does introduce a very small overhead to the L2, with squash requiring the use
of certain cheque indexes be discontinued.

### Considered Alternatives

\-

## Consequences

This modifies the previously proposed data structure, and introduces more
constraints on existing steps.
