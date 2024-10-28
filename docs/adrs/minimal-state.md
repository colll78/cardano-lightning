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

This minimal version follows the [minimal lifecycle](./minimal-lifecycle.md). In
particular there is no `sub` step.

Recall that a staged channel is represented by a utxo at tip. This utxo channel
has an address, value, and datum. A reference script is illegal.

The address's payment credential corresponds to the Cardano Lighting script
associated to the channel currency. Note that the channel currency is determined
by a script parameter. Thus, channels with different currencies will belong to
different addresses.

The value contains a thread token and either:

- Just ada
- Just ada and the channel currency, where the ada covers the min ada
  requirements.

The [thread token](./thread-token.md) records the channel id in its token name.
The channel **total** is amount of the currency in the utxo.

## Decision

### Overview

#### Datum

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
type Hash32 = ByteString -- 32 bytes
type Pubkey = Hash32

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

#### Cheque

A cheque is a declaration from one partner to the other that they own them
funds.

A normal cheque has no conditions. A locked cheque is conditional.

```haskell
data Lock
  = Blake2b256Lock Hash32
  | Sha2256Lock Hash32
  | Sha3256Lock Hash32

data Timestamp = Int
data Deadline = Timestamp

data Cheque
  = NormalCheque Index Amount
  | HtlcCheque Index Amount Deadline Lock

type Sig64 = ByteString -- 64 bytes
type Secret = Bytestring -- <= 64 bytes

data Signature
  = Ed25519Signature Sig64
  | EcdsaSecp256k1Signature Sig64
  | SchnorrSecp256k1Signature Sig64

data SignedCheque
  = SignedNormalCheque Cheque Signature  -- Only NormalCheque
  | SignedLockedCheque Cheque Signature Secret
  -- ^ Only LockedCheque
```

A normal cheque is valid if the signature belongs to the anticipated key.

An Htlc cheque is valid if the:

- signature is valid
- deadline has not expired
- secret of the lock has been provided

#### Squash

We introduce the notion of a `Squash`. This provides a way to aggregate cheques.

```haskell
data Squash = Squash
  { amt : Int
  , idx : Int
  , exc : [Int]
  }

data SignedSquash
  = SignedSquash Squash Signature
```

TBC : Restrict to `Ed25519` signatures only.

The squash prevents an ever increasing list of cheques.

A signed squash is valid if the signature is valid with respect to the
anticipated key. With regards to a channel this will be one of the two partners.
With regards to a step being performed by one partner, this will be the key of
the other partner.

A partner should verify that the squash aligns with their understanding of what
they are owed. That is, the amount is at least what it should be given the
`(inc, exc)` provided. If they do not agree with the new squash, they should
close the channel with the previous squash in the receipt.

#### Receipt

A receipt is a squash and list of cheques

```haskell
data Receipt = Receipt SignedSquash [SignedCheque]
```

The receipt is used in a close or resolve step. It is constructed by the partner
performing the step.

A valid receipt will include a valid signed squash, and list of valid signed
cheques. Moreover, the cheques must have unique indices and are all unaccounted
for in the squash.

### Rationale

Motivations:

- Minimal data required on-chain or within transactions, while
- Sufficient for safety, and
- Being straightforward to reason about.

To justify that this data is sufficient, we must consider each step, and what
happens to the data. This is a first approximation of an L1 spec.

#### L2

##### Cheque

While the channel is open, the partners can safely exchange cheques. A cheque
represents value owed from the sender to recipient. The cheque must have a valid
signature.

The signature is formed on the concatenation of the channel id and the payload

> ::: TBC ::: What is signed? `cid . payload` ?

Cheques have an index. The index is treated as a monotonically increasing
sequence.

A cheque can be **raised**. A cheque is raised if a second signed cheque is
sent, with an index already in use.

To be considered valid, the receiver will verify that:

- The amount of the cheque must be greater.
- This index must not have been accounted for in a previous squash (see below).

The L1 will only except one cheque per index, thus on a close or resolve step,
the partner is motivated to include the latest cheque per index.

Similarly, a locked cheque can be **unlocked**. The sender reissues a cheque
with the same index, but of constructor `NormalCheque`. This will prevent the
need to use the cheque on the L1 before the deadline expires.

Again the receiver will verify that:

- The value matches (or is at least) that of the normal cheque.

##### Squash

Periodically, partners can request and exchange a squash. This aggregate the
amounts in the cheques to date.

The squash includes the index (`idx`) of the highest cheque included in the
aggregate.

If there are pending locked cheques or cheque indices that a partner believes
will still be utilised via raises, and these have a relative low index, then
they can be included in the exclusion list (`exc`).

All cheques that contribute to the amount in the squash are said to be
**acounted** for. All other cheques are considered **unaccounted**.

A squash must be signed similarly to a cheque.

#### L1 steps

##### Open

On an `open`:

- the thread token is minted.
- the outputs contain channel utxo with
  - the address equal to script address (ignoring staking)
  - the value is either, depending on the channel currency:
    - the thread token and ada, or
    - the thread token, min ada, and an amount of the currency token
  - the datum is `Opened` with params `OpenedParams pk0 pk1 0`.

`pk0` belongs to the partner performing the open. `pk1` belongs to the other
partner and has been communicated off-chain.

The partner (who did not open the channel) has yet to partake in the channel.
Thus none of their funds are at risk.

Before stepping the channel themselves, the partner will have checked that the
state is good. For example, the channel has sufficient funds.

The thread token name is determined by some seed input, and cannot be re-minted.

The _continuing output_ is the output of the transaction containing the thread
token. It must be at the same address as the input. The datum is an inlined
datum.

##### Add

On an `add`:

- The tx is signed by exactly one of the partners
- The total funds of the continuing output has increased by `x >= minIncrease`.
- If the signer is `pk0`, then the datum is unchanged.
- Else, the `amt1` is increased by `x`.

Exactly one of the two partners is involved in the transaction.

No funds can be removed. The `minIncrease` prevents spam additions.

#### Close

On a `close`:

- The tx is signed by `closer`, who is one of the partners.
- The receipt is valid with respect to the other partners key, `other`. The
  total is of `t` funds.
- The transaction has validity range with upper bound `ub`.
- The continuing value has at least the same funds
- The continuing datum has
  `ClosedParams closer other amtCloser (ub + resolutionPeriod)` where
  `amtCloser` is
  - if `closer == pk0`, then `(total - amt) + t`
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
- The receipt is valid with respect to the closer `key`. The total is of `t`
  funds.
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
