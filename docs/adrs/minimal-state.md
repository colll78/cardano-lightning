---
title: "Minimal state"
status: proposed
authors:
  - "@waalge"
  - "@paluh"
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

The minimal lifecycle refers to "off-chain transacting" without providing any
further details. It is necessary to understand the aspects of this off-chain
transacting that have a direct bearing on the L1.

## Decision

### Overview

#### Cheque

A cheque is a sent from one partner of the channel to the other and indicates
that the amount of funds owed from the sender to the receiver. Cheques make up a
core part of the off-chain transacting and are used when settling the L2 state
on the L1.

There are two types of cheque: normal, and locked. Locked cheques are valid (on
settling) only if some other conditions are met. For now we only consider Hash
Time Lock Contract (Htlc) type locked cheques.

```haskell
data Index = Int -- >=0
data Amount = Int

data Normal
  = Normal Index Amount

type Hash32 = ByteString -- 32 bytes

data Lock
  = Blake2b256Lock Hash32
  | Sha2256Lock Hash32
  | Sha3256Lock Hash32

data Locked
  = Htlc Index Amount Deadline Lock

data Cheque
  = NormalCheque Normal
  | LockedCheque Locked

type Secret = Bytestring -- <= 64 bytes

data Unlocked =
  Unhtlc Htlc Secret

data MCheque
  = MNormal Normal
  | MLocked Locked
  | MUnlocked Unlocked

type Sig64 = ByteString -- 64 bytes

data Signature = Sig64

data Signed T = Signed T Signature
```

On receiving a signed cheque, the receiver verifies that it is acceptable:

- the sender's signature is correct
- the index is not yet accounted for in an existing snapshot
- the amount is sufficient for their expectation
- if the check is locked, then other conditions are satisfied such as the
  deadline is sufficiently far into the future.

##### Signing cheques

As with other signed objects, we prepend the channel id (`cid`) onto the data.
The channel id effectively acts as a nonce. The signature for a cheque is for
the message

Sign:

```
message = concat cid (asBytes cheque)
signature = sign signingKey message
```

Verify:

```
Signed cheque siganture = signedCheque
message = concat cid (asBytes cheque)
isValid = (verify verificationKey message) == signature
```

The `sign` and `verify` functions are `Ed25519` functions. This aligns with the
signing of txs on Cardano.

##### Normalising cheques

There is a process by which a locked cheque is 'replaced' into a normal cheque.
We call this 'normalising' a cheque.

An Htlc cheque can be settled if the deadline has not passed, and the receiver
knows the secret. In such case, the receiver can construct settle using the
`NonLockedCheque` type. However, this would require closing the channel.

Thus if a sender wishes for the channel to remain open, they must normalise the
cheque. The sender sends a signed normal cheque with the same index and amount
as the locked one. The normal cheque can be settled at any time.

If the sender fails to normalise a locked cheque then the receiver should close
the channel, settling the cheque.

Note that in a settle, submitted cheque must have unique indices. The receiver
could not use both the locked and normal cheque.

##### Raising cheques

There is a process by which a cheque is 'replaced' by one of a greater amount.
We call this 'raising' a cheque. Raising allows for the reuse of a cheque index,
and can facilitate features such as parallel stream payment.

Note that in a settle, submitted cheque must have unique indices. The receiver
could use only the cheque of greatest value per index.

##### Maybe unlocked cheques

At a settle, the partner may know the conditions for unlocking a locked cheque.
Together with their unaccounted for normal and locked cheques, they provide
these as unlocked cheques. For HTLC cheques, a 'secret' is required that when
hashed equals the lock.

Different hashing regimes are supported. These should be attached to the cheque,
not the secret.

#### Snapshot

A snapshot provides a way to aggregate amounts from cheques exchanged in the L2.
It includes the L2 amounts and indicates which cheques have been **accounted**
for, and by its complement, which are **unaccounted** for.

A snapshot can be used when stepping the channel. When used, it provides a lower
bound on the future settlement.

```haskell
data Exclude = [Index]

data Squash =
  { amt :: Amount
  , idx :: Index
  , exc :: Exclude
}

data Snapshot = Snapshot
  { sq0 :: Squash
  , sq1 :: Squash
  }
```

A **squash** gets its name from representing a set of cheques 'squashed' into a
smaller piece of data.

The `amt` is the cumulative total of all cheques of index `idx` or less that do
not appear in the exclusion list `exc`.

To be considered wellformed `exc` is a monotonically increasing list of indices
that are strictly less than `idx`.

`sq0` represents all the cheques _received_ by the partner of key `vk0`. Thus
the `sq0 .^ amt` is the amount `vk0` is owed by `vk1`.

A partner should only send squashes with values monotonically increasing in
amount.

Partners do not necessarily share a context. Actions are happening
asynchronously. Two snapshots may both be valid representations of a state. We
introduce an operation to unify two snapshots. Snapshots can be unioned by
taking the respective squashes with greatest amount.

```haskell
unionSnapshot :: Snapshot -> Snapshot -> Snapshot
unionSnapshot (Snapshot sq00 sq10) (Snapshot sq01 sq11)
  = Snapshot sq0 sq1
    where
      sq0 = (sq00 .^ amt) < (sq01 .^ amt) ? sq01 :? sq00
      sq1 = (sq10 .^ amt) < (sq11 .^ amt) ? sq11 :? sq10
```

Note that this is not a symmetric operation. If the amount appearing in
respective squashes are equal then we use the left argument. In practice, a
partner should only sign and accept monotonically increasing snapshots. That is,
in which the squash amounts are increasing.

Once a cheque is included in a snapshot, it is accounted for. It is unsafe for a
partner to accept an accounted for cheque, since it cannot be used in a settle.

##### Signing snapshots

This works analogously to signatures of cheques. That is, its `Ed25519`, and the
message is the concatenation of the channel id and the snapshot.

Signed snapshots should be exchanged periodically.

##### Handling snapshots

There is not a unique way for a partner to form a snapshot. For example, one
partner. The criteria of what is deemed an acceptable snapshot is to be worked
out elsewhere. If a partner is unhappy with a snapshots provided, they should
close the channel.

Note that once a cheque is accounted for in a snapshot, it should not be raised.
A partner should not accept a cheque already accounted for.

#### Receipt

A receipt consists of a snapshot and unaccounted (maybe unlocked) cheques.

```haskell
data Receipt = Receipt (Signed Snapshot) [(Signed MCheque)]
```

The receipt is used in a close or resolve step. It is constructed by the partner
performing the step.

A valid receipt will include a valid signed snapshot, and list of valid signed
non-locked cheques and valid locked cheques. Moreover, the cheques must have
unique indices and are all unaccounted for in the snapshot.

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
type VerificationKey = ByteString -- 32 bytes,

data OpenedParams = OpenedParams
  { vk0 :: VerificationKey
  , vk1 :: VerificationKey
  , amt1 :: Amount
  , snapshot :: Snapshot
}


data LockedChequeReduced = HtlcRed Amount Deadline Lock

data ClosedParams = ClosedParams
  { closer :: VerificationKey
  , other :: VerificationKey
  , amtCloser :: Amount
  , deadline :: Deadline
  , snapshot :: Snapshot
  , lcrsCloser :: [LockedChequeReduced]
}

Snapshot 400000 123 [23 113] 4423 [432] -- vk0 -> vk1
Snapshot 440000 123 [113] 4423 [432] -- Normalization

s0 -> Snapshot (400000 8 [6]) (1232103 12 []) -- vk0 -> vk1
s1 -> Snapshot (440000 10 [9]) (1238278 4 [3]) -- vk1 -> vk0
s0 AND s1 ~> Snapshot (440000 10 [9]) (1232103 12 [])

Snapshot 460000 123 [23 113] 4423 [432] -- Illegal!
Snapshot 450000 123 [133] 4423 [432] -- Illegal!
Snapshot 500000 124 [123 23 133] 4423 [432] -- Illegal!

  = case (compare idx00 idx01 , compare ex00 exc01 , compare idx10 idx11 , compare exc10 exc11)  of
-- ! Increasing
isLaterThan (Snapshot _ idx00 exc00 idx10 exc10) (Snapshot _ idx01 exc01 idx11 exc11)
  = case (compare idx00 idx01 , compare ex00 exc01 , compare idx10 idx11 , compare exc10 exc11)  of
    (Less, _ , Less, _) -> False
    (Greater, _ , Greater, _) -> True
    (Equal, Less, Less, _) -> False
    _ -> False



data ResolvedParams = ResolvedParams
  { closer :: VerificationKey
}

data ElapsedParams = ElapsedParams
  { other :: VerificationKey
}
```

Pending locked cheques are...

The constructors of locked cheque reduced correspond to those of locked cheques.
It is reduced since the index is not longer relevant and the amount is handled
in the utxo value. What remains is the conditions of the lock.

A few remarks on some of the fields.

- `Opened .^ amt1` represents the amount of funds in the channel that belong to
  the partner with key `Opened .^ vk1`.
- Similarly `Closed .^ amtCloser` is the amount of funds that belong to the
  partner with key `Closed .^ closer`.

#### Redeemer

Redeemer constructors align with steps.

```haskell
data Redeemer
  = Open OpenParams
  | Add AddParams
  | Close CloseParams
  | Resolve ResolveParams
  | Elapse
  | End
```

### Rationale

Motivations:

- Minimal data required on-chain or within transactions, while
- Sufficient for safety, and
- Being straightforward to reason about.

To justify that this data is sufficient, we must consider each step, and what
happens to the data. This is a first approximation of an L1 spec.

#### L1 steps

##### Open

On an `open`:

- the thread token is minted.
- the outputs contain channel utxo with
  - the address equal to script address (ignoring staking)
  - the value is either, depending on the channel currency:
    - the thread token and ada, or
    - the thread token, min ada, and an amount of the currency token
  - the datum is `Opened`.

`vk0` belongs to the partner performing the open. `vk1` belongs to the other
partner and has been communicated off-chain.

The partner (who did not open the channel) has yet to partake in the channel.
Thus none of their funds are at risk.

Before stepping the channel themselves, the partner will have checked that the
state is good. For example, the channel has sufficient funds. Typically, the
datum will have the value

```haskell
OpenedParams vk0 vk1 0 (Snapshot 0 0 [] 0 [])
```

However, there are no constraints on this. For example, it is possible to open
with a fee to the partner by setting `amt1 > 0`.

The thread token name is determined by some seed input and cannot be re-minted.

For all future steps, the _continuing output_ is the output of the transaction
containing the thread token. It must be at the same address as the input. The
datum is an inlined datum.

##### Add

On an `add`:

- The tx is signed by exactly one of the partners
- The total funds of the continuing output has increased by `x >= minIncrease`.
- For the continuing datum
  - the keys are unchanged
  - If the signer is `vk0`, then `amt1` is unchanged else the `amt1` is
    increased by `x`.
  - If a signed snapshot is provided and

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
  - if `closer == vk0`, then `(total - amt) + t`
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
- The receipt is valid with respect to the closer key `other`. The total is of
  `t` funds.
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
