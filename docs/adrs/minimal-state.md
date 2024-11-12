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

#### Cheques

A cheque is a sent from one partner of the channel to the other and indicates
that the amount of funds owed from the sender to the receiver. Cheques make up a
core part of the off-chain transacting and are used when settling the L2 state
on the L1.

There are two types of cheque: normal and locked. Locked cheques are valid (at
settle) only if some given conditions are met. For now we only consider Hash
Time Lock Contract (Htlc) type locked cheques, but with an eye on variations
such as the Point Time Lock Contract.

```haskell
type Index = Int -- >=0
type Amount = Int
type Timeout = Int -- Posix timestamp

data Normal
  = Normal Index Amount

type Hash32 = ByteString -- 32 bytes

data Lock
  = Blake2b256Lock Hash32
  | Sha2256Lock Hash32
  | Sha3256Lock Hash32

data Locked
  = Htlc Index Amount Timeout Lock

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
type Signature = Sig64

data Signed T = Signed T Signature
```

On receiving a signed cheque, the receiver verifies that it is acceptable:

- the sender's signature is correct
- the index is not yet accounted for in an existing snapshot
- the amount is sufficient for their expectation
- if the check is locked, then other conditions are satisfied such as the
  timeout is sufficiently far into the future.

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

If a receiver of a locked cheque knows the secret preimage of the lock prior to
the locked cheques timeout, then they are capable of claiming the associated
funds. If they wait until after the timeout, they are no longer able to claim
the funds. To avoid the unnecessary closure of the channel, the receiver
demonstrates they know the secret and request normalising the cheque.

The sender, wishing for the channel to remain open, normalises the cheque. The
sender sends a signed normal cheque with the same index and amount as the locked
one. The normal cheque can be settled at any time.

If the sender of the locked cheque does not comply in good time, the receiver
should proceed by closing the channel and claiming the funds with the secret. In
such case, the receiver can construct settle using the `NonLockedCheque` type.

Note that in a settle, submitted cheque must have unique indices. The receiver
could not use both the locked and normal cheque.

##### Raising cheques

There is a process by which a cheque is 'replaced' by one of a greater amount.
We call this 'raising' a cheque. Raising allows for the reuse of a cheque index,
and can facilitate features such as parallel stream payment.

Note that in a settle, submitted cheque must have unique indices. The receiver
could use only the cheque of greatest value per index.

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

The `amt` is the cumulative total of all cheques of index **strictly less** than
`idx` and that do not appear in the exclusion list `exc`. In particular a cheque
with index `>= idx` is unaccounted for.

To be considered wellformed `exc` is a monotonically increasing list of indices
that are strictly less than `idx - 1`.

`sq0` represents all the cheques _received_ by the opener ie partner of key
`vk0 = fst keys`. Thus the `sq0 .^ amt` is the amount `vk0` is owed by `vk1`.

A partner should only send squashes with values monotonically increasing in
amount.

Partners do not necessarily share a context. Actions are happening
asynchronously. Two snapshots may both be valid representations of a state. We
introduce an operation to unify two snapshots. Snapshots can be unioned by
taking the respective squashes with greatest amount.

```haskell
max :: Squash -> Squash -> Squash
max sq0 sq1 = (sq0 .^ amt) < (sq1 .^ amt) ? sq1 :? sq0

unionSnapshot :: Snapshot -> Snapshot -> Snapshot
unionSnapshot (Snapshot sq00 sq10) (Snapshot sq01 sq11)
  = Snapshot (max sq00 sq10) (max sq01 sq11)
```

Note that this is not a symmetric operation. If the amount appearing in
respective squashes are equal then we use the left argument. In practice, a
partner should only sign and accept monotonically increasing snapshots. That is,
in which the squash amounts are increasing.

Once a cheque is included in a snapshot, it is accounted for. It is unsafe for a
partner to accept a cheque that has been accounted for since it cannot be used
in a settle.

##### Signing snapshots

This works analogously to signatures of cheques. That is, its `Ed25519`, and the
message is the concatenation of the channel id and the snapshot.

Signed snapshots should be exchanged periodically.

##### Handling snapshots

There is not a unique way for a partner to form a snapshot. The precise criteria
of what is deemed an acceptable snapshot for a given participant in a particular
context is to be worked out elsewhere. If a partner is unhappy with a snapshot
provided, and they cannot resolve this issue with their partner, they should
close the channel.

A partner should only accept cheques that can be settled together with the last
acceptable snapshot they received from their partner. There will be a limit on
the number of cheques that can be handled in a settle. The exact numbers will be
established elsewhere.

#### Receipt

A receipt consists of a snapshot and unaccounted (maybe unlocked) cheques.

```haskell
data Receipt = Receipt (Maybe (Signed Snapshot)) [(Signed MCheque)]
```

The receipt is used in a close or resolve step. It is constructed by the partner
performing the step.

A valid receipt will include a valid signed snapshot, and list of valid signed
non-locked cheques and valid locked cheques. Moreover, the cheques must have
unique indices and are all unaccounted for in the snapshot.

The logic should fail if the indices of the `MCheque`s are not strictly
increasing.

#### Datum

A digression. Abstractions are generally not free of costs. Cardano script
execution is a highly constrained environment, where costs and execution limits
are immediately a cause for concern. For that reason implementation details we'd
like to ignore must unfortunately encroach on design.

For a validator employed with a spend purpose to learn its own script hash, it
must:

- extract its own output reference from its args,
- find the input with matching output reference,
- extract the hash from the payment credentials.

All this is relatively expensive and is quadratic in the number of inputs. It is
cheaper to access the data from the datum, which is present as an argument, and
this is linear in the number of arguments.

```haskell
data ScriptHash = ByteArray -- 28 bytes
type VerificationKey = ByteString -- 32 bytes,
type Keys = (VerificationKey, VerificationKey)
data Datum = (ScriptHash, Keys, Stage)
```

There are some scenarios where one of the two keys is no longer strictly
necessary. For example, elapsed stage with no pending locked cheques for the
closer. However, we do will not consider optimising for these niche cases.

> ::: WARNING ::: The order in which the keys appears matters and can change on
> a close step. Details below.

The channel datum has the following form where the constructors follow the
stages of the lifecycle.

```haskell
data Stage
  = Opened OpenedParams
  | Closed ClosedParams
  | Responded RespondedParams
  | Elapsed ElapsedParams
  | Resolved ResolvedParams
```

The params are as follows

```haskell
data OpenedParams = OpenedParams
  { amt1 :: Amount
  , snapshot :: Snapshot
  -- ^ defaults to `Snapshot (Squash 0 0 []) (Squash 0 0 [])`
}
```

- The keys should be ordered `(opener, non-opener)`.
- `amt1` is the amount of channel funds that belong to the not-opener partner.
  Typically this will start at 0 as all funds are provided by the opener.
  However, this is not enforced and up to the partners to decide.
- `snapshot` provides the ability to place a lower bound for the eventual
  settled state. This allows partners to know, and limit an upper bound on
  potential losses in the case of some catastrophic failure.

```haskell
data LockedChequeReduced = HtlcRed Amount Timeout Lock
data Pend = Pend Amount [LockedChequeReduced]

data ClosedParams = ClosedParams
  { amt0 :: Amount
  , sq :: Squash
  , timeout :: Timeout
  , pend :: Pend
}
```

- A `Pend` encapsulates the total value from a list of pending locked cheques,
  together with the information required to free them, either via a secret, or
  their expiry. To be accepted by the L1 the length of the list must not exceed
  `maxLockedCheques`.
- A pend is empty if it is `Pend 0 []`.
- The total prevents the need to walk the list. FIXME :: Is this needed ?!

- The keys are ordered `(closer, non-closer)`. This is the order in which they
  will remain for the rest of the lifecycle.
- `amt0` is the amount of the funds that belong to the closer, according their
  receipt and the previous state. It does not reflect the receipt of the
  non-closer who is yet to settle. The calculation is described below.
- `sq` is the latest squash for the non-closer, that is, the squash representing
  the cheques received by the `non-closer`.
- `expiry` is the time after which the closer may perform an `elapse` step
- `pend` contains the relevant bits of information of any pending locked
  cheques.

```haskell
data ResolvedParams = ResolvedParams
  { amt0 :: Amount
  , pend0 :: Pend
  , pend1 :: Pend
}
```

- `amt0` has the same meaning as above, but now reflects the receipt provided by
  the non-closer partner.
- `pend0` - is the pending locked cheques received by the closer
- `pend1` - is the pending locked cheques received by the non-closer

```haskell
data ElapsedParams = ElapsedParams
  { pend :: Pend
}
```

- `pend` - is the pending locked cheques received by the closer

#### Redeemer

Redeemer constructors align with steps.

```haskell
data Redeemer
  = Open OpenParams
  | Add AddParams
  | Close CloseParams
  | Resolve ResolveParams
  | Elapse ElapseParams
  | Recover RecoverParams
  | Free FreeParams
  | End
```

We will make these explicit in the spec.

### Rationale

Motivations:

- Minimal data required on-chain or within transactions, while
- Sufficient for safety, and
- Being straightforward to reason about.

To justify that this data is sufficient, we must consider each step, and what
happens to the data. This is a first approximation of an L1 spec.

#### L1 steps

A step corresponds to a channel and tx. A single transaction may step multiple
channels simultaneously. They are embarrassingly parallel.

Channels are distinguished by a thread token encoding the channel id. The thread
token name is determined by some seed input and cannot be re-minted. Details of
the thread token are found in [channel-id](./channel-id.md).

A (staged) channel is represented by a single utxo at time at any one time. All
steps that do not unstage the channel have a _continuing output_, the output of
the transaction containing the thread token. It necessarily has the following
properties:

- After the open, the continuing output must be at the same address as the
  input.
- The value is either (depending on the channel currency):
  - the thread token and ada, or
  - the thread token, min ada, and an amount of the currency token
- The datum is an inlined datum.

The amount in the channel utxo of the channel currency is called the **total
funds**.

Each transaction is signed by precisely one of the partners. Any snapshot or
cheque provided as part of that transaction will require the signature of the
other partner.

In the following we take this as given. We may frame the conditions in terms of
the change between the input and continuing output.

##### Open

On an `open`:

- the thread token is minted.
- the continuing output has
  - the address is equal to script address (ignoring staking)
  - the stage is `Opened`.

`vk0 = fst keys` belongs to the opener. `vk1` belongs to the non-opener and has
been communicated off-chain.

The non-opener has yet to partake in the channel. Thus none of their funds are
at risk.

Before stepping the channel themselves, the non-opener will have checked that
the state is good. For example, the channel has sufficient funds. Typically, the
stage will include the default snapshot. However, there are no constraints on
this. For example, it is possible to open with a fee to the partner by setting
`amt1 > 0`.

##### Add

On an `add`:

- The total funds has increased by `x >= minIncrease`.
- If the tx is signed by `vk0`
  - then the continuing `amt1` is unchanged
  - else it is `amt1 + x`.
- If a signed snapshot is provided then continuing snapshot is the union of this
  with the previous.

No funds can be removed. The `minIncrease` prevents spam additions.

#### Close

On a `close`:

- The transaction has validity range with upper bound `ub`.
- The continuing value has at least the same funds
- The keys are possibly reordered to be `(closer, non-closer)`.
- The receipt is valid (see above).
- The continuing stage is `ClosedParams amt0 sq expiry pend` where
  - `amt0` is a calculated by
    - the amount already recorded (either `total - amt1` if the closer is also
      the open, else `amt1`)
    - plus the difference of squashes in the latest snapshot (correctly signed)
    - plus the additional cheques not yet accounted for excluding pending
      cheques.
  - `sq` is the latest squash corresponding to the non-closer
  - `expiry >= ub + respondPeriod`
  - `Pend p0 lcrs = pend`, where `p0` is the total of all the locked cheques
    presented in the receipt, and the lcrs is no greater in length than
    `maxLockedCheques`.

The amount calculation.

```haskell
  amt0 = prev + new + cheque
    where
      is0 = closer == vk0
      prev = if is0 then (total - amt1) else amt1
      diff = (snapshot .^ sq0 .^ amt - snapshot .^ sq1 .^ amt )
      new = if is0 then diff else (- diff)
      cheque = foldl mc
```

No funds are removed.

Regardless of how large or small the `ub` or `expiry` is, the non-closer has at
least least `respondPeriod` to perform a `respond`.  
If `expiry` is large, the closer is only postponing their ability to `elapse`
the channel were they to need to.

The tx size is in part linear in the number of cheques. Both partners must
ensure that the size of this transaction is sufficiently small to meet the L1 tx
limits. They must perform a `close` step before the number of cheques in their
possession exceeds these limits. If they do not, they put only their own funds
at risk - not their partners.

#### Respond

On a `respond`:

- The continuing value has `amt` funds, where `amt` is a calculated by
  - the previous total
  - minus the new `amt0`
  - minus the total of the closer's pending cheques
  - minus the total of the non-closer's pending cheques
- The continuing stage is `RespondedParams amt0 pend0 pend1` where
  - `amt0` is a calculated by
    - the previous `amt0`
    - minus the difference of squashes if a new snapshot is provided.
    - minus the total of the unaccounted for cheques.
  - `pend0` is pend list of the closer, potentially with expired cheques dropped
    and the total adjusted accordingly.
  - `pend1` is the pend list of the non-closer.

Both partners have now submitted their receipt as evidence of how much they are
owed from their off-chain transacting.

At this point the L1 has all the information as to how much both participants
are eligible to claim from the channel.

As with a close the tx size is linear in the number of cheques. Both partners
must ensure they would be able to `close` or `resolve` all their cheques,
without hitting tx limits.

#### Elapse

On an `elapse`:

- The tx validity range lowerbound `lb` and `lb > expiry`.
- The continuing amount is `total - amt0 - freedAmt`.
- The continuing stage is `Elapsed pend`, where `pend` is as the input, but
  where some locked cheques may be freed with a total amount of `freedAmt`.

The non-closer has failed to meet their obligation of providing their receipt.
The closer may now release their funds.

The closer can take the opportunity to free any pending cheque at the same time.

#### Termination

If the channel is in a post-opened stage (closed, responded, elapsed), and the
channel value falls below `minChannelFunds`, then it is treated as dust and can
be terminated.

The terminating steps from either a resolved stage on an elapsed stage require
the tx to have a valid signature from the remaining partner.

There is no continuing output. The thread token is burnt.

## Discussion, Counter and Comments

\-

### Comments

\-

### Considered Alternatives

\-

## Consequences

For now this is foundational. There are no further consequences.
