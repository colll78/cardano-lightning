---
title: "Minimal state"
status: proposed
authors: "@waalge"
date: 2024-10-24
tags:
  - l1
---

## Context

A (staged) CL channel consists of 2 partners and a utxo at tip. We need to
establish what information needs to be tracked and where.

This minimal version follows the minimal channel lifecycle. In particular there
is no `sub` step.

## Decision

### Overview

A staged channel is represented by a utxo at tip.

The value contains a thread token and either:

- Just ada
- Just min ada and the channel currency

Note that the channel currency is determined by a script parameter. Thus,
channels with different currencies will belong to different addresses.

The thread token records the channel id in its token name.

The channel total is amount of the currency in the utxo.

The channel datum has the following form

```haskell
data Datum
  = Opened OpenedParams
  | Closed ClosedParams
  | Resolved ResolvedParams
  | Elapsed ElapsedParams
```

The constructors follow the stages of the lifecycle.

```haskell
data OpenedParams = OpenedParams {
  pk0: Pubkey,
  pk1: Pubkey,
  amt1: Int,
}

data ClosedParams = ClosedParams {
  closer: Pubkey,
  other: Pubkey,
  amtCloser: Int,
  deadline: Timestamp,
}

data ResolvedParams = ResolvedParams {
  closer: Pubkey,
}

data ElapsedParams = ElapsedParams {
  other: Pubkey,
}
```

### Rationale

Motivations:

- Minimal data required on-chain or within transactions, while
- Sufficient for safety, and
- Being straightforward to reason about.

To justify that this data is sufficient, we must consider each step, and what
happens to the data. This is a first approximation of an L1 spec.

#### Steps

##### Open

On an `open`:

- the thread token is minted.
- the outputs contain channel utxo with
  - the address equal to script address (ignoring staking)
  - the value is either, depending on the channel currency:
    - the thread token and ada, or
    - the thread token, min ada, and an amount of the currency token
  - the datum is `Opened` with params `OpenedParams ownKey otherKey 0`.

The partner (who did not open the channel) has yet to partake in the channel.
Thus none of their funds are at risk.

Before stepping the channel themselves, they will have checked that the state is
good. For example, the channel has sufficient funds.

The thread token name is determined by some seed input, and cannot be re-minted.

The _continuing output_ is the output of the transaction containing the thread
token. It must be at the same address as the input. The datum is an inlined
datum.

##### Add

On an `add`:

- The tx is signed by exactly one of the partners
- The total funds of the continuing output has increased by `x >= minIncrease`.
- If the signer is `ownKey`, then the datum is unchanged.
- Else, the `amt1` is increased by `x`.

Exactly one of the two partners is involved in the transaction.

No funds can be removed. The `minIncrease` prevents spam additions.

#### Close

On a `close`:

- The tx is signed by `closer`, who is one of the partners.
- All cheques submitted have valid signatures from `other`. Say the total amount
  of the cheques are `t`.
- The transaction has validity range with upper bound `ub`.
- The continuing value has at least the same funds
- The continuing datum has
  `ClosedParams closer other amtCloser (ub + resolutionPeriod)` where
  `amtCloser` is
  - if `closer == ownKey`, then `(total - amt) + t`
  - else `amt + t`

Exactly one of the two partners is involved in the transaction.

No funds are removed.

Regardless of how large or small the `ub` is, the `other` partner, will have at
least `resolutionPeriod` to submit a `resolve`.  
If the closer did submit a large `ub`, they would only be postponing their own
ability to `elapse` the channel were they to need to.

The tx size is in part linear in the number of cheques. Both partners must
ensure that the size of this transaction is sufficiently small to meet the L1 tx
limits. They must perform a `close` step before the number of cheques in their
possession exceeds these limits. If they do not, they put only their own funds
at risk - not their partners.

#### Resolve

On a `resolve`:

- The tx is signed by `other`.
- All cheques submitted have valid signatures from `closer`. Say the total
  amount of the cheques are `t`.
- The continuing value has `amtCloser - total - t`. (TODO : Check)
- The continuing datum has `ResolvedParams closer`.

Both partners have now submitted their evidence of how much they are owed from
their off-chain transacting.

At this point the L1 has all the information as to how much both participants
are eligible to claim from the channel.

As with a close the tx size is linear in the number of cheques. Both partners
must ensure they would be able to `close` or `resolve` all their cheques,
without hitting tx limits.

#### Elapse

On an `elapse`:

- The tx is signed by `closer`.
- The tx validity range lowerbound is after the `deadline`.
- The continuing datum has `ElapsedParams other`.
- The continuing amount is (at least) `total - amtCloser`.

Both partners have now submitted their evidence of how much they are owed from
their off-chain transacting.

At this point the L1 has all the information as to how much both participants
are eligible to claim from the channel.

The '(at least)' prevents any chance of invalidity due to violating minAda
rules. Both parties should keep themselves safe by ensuring their L2 balances
are clear of this problem anyway.

The `other` partner may lose funds, but they have not performed their obligation
within the pre-agreed time fame.

#### Termination

The terminating steps from either a resolved stage on an elapsed stage require
the tx to have a valid signature from the remaining partner.

There is no continuing output. The thread token is burnt.

## Discussion, Counter and Comments

\-

### Comments

\-

#### Locked cheques

There is a small extension required in the context of locked cheques. In this
case, the cheque has valid signature, but also preimage and the deadline is
after the upper bound. Again both partners are responsible for ensuring that
their collection of cheques can be handled in a single `close` or `resolve`.

### Considered Alternatives

\-

## Consequences

For now this is foundational. There are no further consequences.
