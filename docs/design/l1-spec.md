---
title: CL L1 Spec
author:
  - "@waalge"
  - "@paluh"
---

## Intro

Cardano Lightning (CL) is p2p payment solution inspired by Bitcoin Lightning
Network, and built over the Cardano blockchain. It is an L2 (Layer 2) optimized
for:

- Near instant settlement
- Scalability

Users of the network maintain two party channels, through which they can send
and receive funds. We may refer to the participants of the channel as the party
and counter party.

A user can perform various high level actions, including:

1. Open, maintain, and end a channel
2. Send, and receive funds

Signposting:

- For gentler intro to CL, check out the blog and the
  [minimal lifecycle ADR](../ards/minimal-lifecycle.md) for a general
  introduction lifecycle.
- For terms, see the [glossary](../glossary.md)
- For explanations on how to read this spec, see the appendix.

## Design

### Overview

CL consists of a single Plutus V3 validator executed in both `Mint` and `Spend`
purpose.

The business logic is entirely implemented when executed with `Mint` purpose.
The `Spend` logic simply verifies the mint logic is executed. This is to
minimize the number of traversals required over the inputs and outputs, when
stepping multiple channels within a single tx.

### Steps and stages

A (staged) channel is represented by a utxo at tip at the script address bearing
a thread token (see [channel id ADR](../adrs/channel-id.md) for more
commentary).

When a channel is 'staged' the thread token is minted; when the channel is
'unstaged' the thread token is burnt. The thread token remains at the script
address.

The stages of a channel are:

- `Opened`
- `Closed`
- `Responded`
- `Resolved`
- `Elapsed`

The steps that progress from one stage to the next are follows:

- `open : [*] -> Opened` : Mints the thread token and adds funds to the
  partner's account.
- `close : Opened -> Closed` : A partner submits their receipt of their L2
  transacting. The partner should no longer accept cheques on the L2.
- `respond : Closed -> Responded` : The non-closer partner submits their
  receipt. They release the funds they are owed, and not still locked.
- `resolve : Responded -> Resolve` : The closer releases the funds they are
  owed, and not still locked.
- `elapse : Closed -> Elapsed` : A closer can release their funds, up to pending
  locked cheques, if the respond is not sufficiently punctual.

Steps that are fixed to a stage

- `add : Opened -> Opened` : Add funds to their account.
- `free : Closed -> Closed` : Closer provides evidence that conditions We'd
  still need to know the latest are met to free some locked cheques. The value
  is added to their account but not released
- `free : Responded -> Responded` : Non-closer provides evidence that conditions
  are met to free some locked cheques. Funds are immediately released.
- `free : Resolved -> Resolved` : Either partner frees locked cheques, and funds
  are immediately released.
- `free : Elapsed -> Elapsed` : A partner adds funds to their account.

Unstaging steps

- `end : Responded -> [*]` : A `resolve` but the output has no locked cheques.
- `end : Resolved -> [*]` : A `free` but the output has no locked cheques.
- `end : Elapsed -> [*]` : Non-closer releases their funds and there are no
  locked cheques.

### Constants

To prevent the size of the datum making it unspendable, we provide a hard limit
on the size of the list of pending cheques.

```ini
max_pend = 20
```

### Token names

Bolt tokens are used to invoke the script in `Mint` purpose, when no thread
token are being minted or burned.

Its name is the thunder bolt emoji.

```aiken
let bolt_token_name = "⚡"
```

Thread tokens are formed in the following manner

```rs
let name = "⚡" + mk_cid(seed, idx)
```

where

- `seed` is the oref of some input spent in the mint.
- `idx` is the relative output index the minting tx outputs the thread token.

```
fn mk_cid(seed, idx) {
  seed |> as_bytes |> push(idx) |> blake_2b_256 |> take(20)
}
```

-

### Data

The following sections are collections of data definitions that are underpin
communication and integrity both within the L2 and from the L2 to the L1.

Relevant data types have an associated `verify` function employed withing the
script that verifies that the data is well-formed.

#### Cheques

Cheques a vehicle through wish funds are sent from one partner to the other. As
such they must be understood on the L1.

Cheques may be "normal" or "locked". Normal cheques, provided they are
accompanied with a valid signature, are indicate the sender owes the receiver
the indicated amount of funds. A locked cheque indicates that the sender owes
the receiver funds subject to extra conditions.

A "hash time locked contract" cheque (HTLC) has a lock in the form of a hash. To
be redeemable, the receiver must provide the "secret" that hashes to the lock.

```aiken
type Index = Int
type Amount = Int
type Timeout = Int // Posix Timestamp

type Normal = (Index, Amount)

type Hash32 = ByteString -- 32 bytes

type Lock {
  Blake2b256Lock(Hash32)
  Sha2256Lock(Hash32)
  Sha3256Lock(Hash32)
}

type Locked {
  Htlc(Index, Amount, Timeout, Lock)
}

type Cheque {
  NormalCheque(Normal)
  LockedCheque(Locked)
}

type Secret = Bytestring // <= 64 bytes

type Unlocked {
  Unhtlc(Htlc, Secret)
}

type MCheque {
  MNormal(Normal)
  MLocked(Locked)
  MUnlocked(Unlocked)
}

type Sig64 = ByteString -- 64 bytes
type Signature = Sig64
type Signed<T> = (T, Signature)
```

As with other signed objects, we prepend the channel id (`cid`) onto the data.
The channel id effectively acts as a nonce. The signature for a cheque is for
the message

To verify a signature:

```aiken
fn verify_cheque( signed_cheque : Signed<Cheque> , vk : VerificationKey) -> Bool {
  let (cheque, siganture) = signed_cheque
  let message = concat cid (as_bytes cheque)
  verify(verificationKey, message == signature
}
```

`verify` functions are `Ed25519` functions. This aligns with the signing of txs
on Cardano.

#### Snapshot

As amounts of funds are transacting on the L2, the list of cheques used grows.
The funds associated to an L2 account can be "squashed down" to a much smaller
piece of data, namely a `Squash`. The partner's squash is the summary of the
cheques they received.

Together, the two partners `Squash`s form a snapshot. The snapshot allows
partners to maintain a manageable amount of  
The squashes are ordered lexicographically by the partners verification key. The
ordering is important.

```aiken
type Exclude = List<Index>
type Squash = (Amount, Index, Exclude)
type Snapshot = (Squash, Squash)
```

A snapshot can be submitted to the L1 as part of an `add`. In doing, it provides
a lower bound on final settlement, Thus it provides a lower bound on potential
loses in a scenario of catastrophic failure in which a partner is off-line and
cannot `respond`.

The verify function works analogously to signatures of cheques.

#### Receipt

The ending of a channel done across several steps. Each partner is responsible
for their own funds. Each partner should **settle** their L2 state on the L1.
This is done with a snapshot, and cheques unaccounted for. The receipt is made
by the submitter, and consists of signed by their partner.

```aiken
type Receipt =  (Option<Signed<Snapshot>>, List<Signed<MCheque>>)
```

If the latest snapshot is already in the L1, there is no need to provide it
again. The list of signed `MCheque`s are the cheques not accounted for in the
snapshot. It may include the pending locked cheques: locked cheques that have a
timeout yet to pass, but no secret is known.

A valid receipt will include a valid signed snapshot, and list of valid signed
non-locked cheques and valid locked cheques. Moreover, the cheques must have
unique indices and are all unaccounted for in the snapshot.

The logic should fail if the indices of the `MCheque`s are not strictly
increasing.

#### Pend

After a close, there may exists pending (locked) cheques. It is yet to be
determined which partner ultimately is rightfully due the associated amounts.

The index of a cheque is no longer relevant

```aiken
type LockedReduced {
  HtlcReduced(Amount, Timeout, Lock)
}

type Pend = (Amount, List<LockedReduced>)
```

A `Pend` encapsulates the total value from a list of pending locked cheques,
together with the information required to free them, either via a secret, or
their expiry. To be accepted by the L1 the length of the list must not exceed
`max_pend` constant. A pend is empty if it is `Pend 0 []`. The total prevents
the need to walk the list. Note that it is to be confirmed whether this total
field provides sufficient benefit to be included.

A pend is correctly derived from a receipt if it is formed the locked cheques,
and the amount is the total amount.

A pend is reduced by secrets, if each secret provided unlocks a cheque. A pend
is reduced by timeout, if each locked cheque with timeout that has demonstrably
passed is dropped. The pend amount must reflect the change in the total.

#### Datum

The channel utxo always has an inlined datum.

The datum consists of the scripts own hash. This allows us to defer safely, and
as efficiently as possible, the business logic to the script employed in `Mint`
purpose.

The datum also consists of the keys and the stage information. The keys, as an
unordered set, endures for the life of the script. Note however the order may
change on a `close`.

```aiken
type ScriptHash = ByteArray // 28 bytes
type VerificationKey = ByteString // 32 bytes,
type Keys = (VerificationKey, VerificationKey)
type Pend = (Amount, List<ChequeReduced>)
type Period = Int // Time delta

type Stage {
  Opened(Amount, Snapshot, Period)
  Closed(Amount, Squash, Timeout, Pend)
  Responded(Amount, Pend, Pend)
  Resolved(Pend, Pend)
  Elapsed(Pend)
}

type Datum = (ScriptHash, Keys, Stage)
```

There are some scenarios where one of the two keys is no longer strictly
necessary. For example, elapsed stage with no pending locked cheques for the
closer. However, we do will not consider optimising for these niche cases.

> ::: WARNING ::: The order in which the keys appears matters and can change on
> a close step. Details below.

The channel datum has the following form where the constructors follow the
stages of the lifecycle.

The order of the pends reflects the order of the keys.

##### Opened stage

Suppose the stage is `Opened(amt1, snapshot, respond_period)`.

`amt1` is the amount of channel funds that belong to the not-opener partner.
Typically this will start at 0 as all funds are provided by the opener. However,
this is not enforced and up to the partners to decide. The keys should be
ordered `(opener, non-opener)`, but beyond the above point, this is of no
further consequence.

The `snapshot` is the latest recorded state of the `L2`. It provides the ability
to place a lower bound for the eventual settled state. This allows partners to
know, and limit an upper bound on potential losses in the case of some
catastrophic failure.

The `respond_period`, as the name suggests is minimum time delta between a
partner may `close` and then `elapse` a channel. Thus it is the time which the
non-closer can `respond`. Participants should ensure this appropriate for their
usage.

##### Closed stage

Suppose the stage is `Closed(amt, squash, timeout, pend)`.

The keys are ordered `(closer, non-closer)`. This is the order in which they
will remain for the rest of the lifecycle.

The `amt` is the amount of the funds that belong to the closer, according their
receipt and the previous state. It does not reflect the receipt of the
non-closer who is yet to settle. The calculation is described below.

The `sq` is the latest squash for the non-closer, that is, the squash
representing the cheques received by the `non-closer`.

The `timeout` is the time after which the closer may perform an `elapse` step.

The `pend` contains the relevant bits of information of any pending locked
cheques received by the closer.

##### Responded stage

Suppose the stage is `Responed(amt, pend0, pend1)`.

The `amt` has the same meaning as in the `Closed` stage, but now reflects the
receipt provided by the non-closer partner.

The `pend0` is the pending locked cheques received by the closer. Between stages
the list may have been reduced either by providing the secret or demonstrating
that its timeout has passed.

The `pend1` is the pending locked cheques received by the non-closer.

##### Resolved stage

Suppose the stage is `Resolved(pend0, pend1)`. The two values have the same
significance as in the `Responded` stage.

##### Elapsed stage

Suppose the stage is `Elapsed(pend)`. The `pend` has the same significance as in
the `Closed` stage.

#### Redeemer

We have redeemers for `Spend` and `Mint`.

```aiken
type SpendRedeemer {
  DeferToMint
}

type MintRedeemer = (Option<OutputReference>, List<PStep>)

type Secrets = List<(Idx, Secret)>

type PStep {
  Continuing {
    Add(Option<Signed Snapshot>)
    Close(Receipt)
    Respond(Receipt, Bool)
    Resolve(Secrets)
    Elapse(Secrets)
    Free(Secrets, Bool)
  }
  End(Secrets)
}
```

Note that the type is called `PStep` rather than `Step`. `PStep`, loosely
inspired by 'pseudo-step'. `PStep` is nested and does not include an `Open`
constructor. This better reflects the handling logic. For example, `open`
doesn't have a script input, and `end` doesn't have an output.

### Channel input/output

All steps, except `open` require exactly one input. `open` requires no inputs
and is dealt with first. All steps that are not `end` require a (single)
continuing output. Since `open` doesn't have an input, its continuing output is
referred as a new output.

#### Channel Id

The channel id is determined by the `seed` and an integer.

`cid = mk_cid(seed, idx)`

The integer allows us to reuse the same seed for multiple opens. For details on
the function `mk_cid`, see the [channel id ADR](./../adrs/channel-id.md).

#### New output

With the script hash and channel id, we can find new outputs from the
`tx.outputs`. A new output:

- Address has payment credentials of own script.
- Value is thread token with channel id `cid` and either:
  - ada
  - ada and channel currency
- Datum is inlined, and has correct `dat.0` own hash.

Note that staking credentials are up to the opener, and are fixed for the
channel's life.

There is no further business logic required in an `open`. Thus the signature is

```aiken
fn new_output(own_hash: ScriptHash, cid : ChannelId, outputs : List<Output>) -> List<Output>
```

Note that the function returns the rest of the list after the new output has
been verified.

The funds at risk are those belonging to the submitter of the tx. The non-opener
must check the state of the channel before participating. For this reason it is
safe not to require further verification.

A small perturbation of `new_output` to `new_outputs`, can instead take the
`seed` and the expected number new outputs.

```aiken
fn new_output(own_cred: Credential, seed: OutputReference, n_mints: Int, outputs : List<Output>) -> List<Output>
```

When `n_mints == 0`, then it return the remaining `outputs`, else it recurs each
time decreasing the `n_mints`.

With this implementation, it makes it easier to use the integer parameter as a
_relative inverse index_. That is, for example, `mk_cid(seed, 3)` appears before
`mk_cid(seed, 2)` in `outputs`.

#### Next input

The validator reduces over the list of steps. At the same time it also reduces
the list of inputs. The "next input" refers to the next input with payment
credentials matching those of the script.

The next input must also have:

- a value including a thread token
- a parse-able datum.

From these, we extract a condensate of the input:
`(cid, address, total, keys, stage)`.

The `next_input` function inspects the item at the head of `tx.inputs` and then
recur over the tail. Thus the function signature is

```aiken
fn next_input(own_cred : Credentials, inputs : List<Input>) -> (cid, address, amount, keys, stage, inputs)
```

If the function exhausts the list, then it fails.

#### Continuing output

A continuing output:

- Same address,
- Same thread token and either:
  - ada
  - ada and channel currency
- Datum is inlined, and has correct `dat.0` own hash

When we extract the continuing output, we return `(Amount, Keys, Stage)` Thus
the function signature is

```aiken
fn get_cont(cid : ChannelId, address : Address, outputs : List<Output>) ->
  (Amount, Keys, Stage, List<Output>)
```

If the output does not have the thread token, the function tries the next
output. If `outputs` is empty, then the function fails. If the thread token is
present and the address is wrong, then fail

#### No (script) inputs

The number of steps in the list of steps must match the number of script inputs.
After we exhaust the steps listed in the redeemer, we must ensure there are no
more inputs from the script.

```aiken
fn no_inputs(own_cred : Credential, inputs : List<Input>) -> Void
```

This fails if any input belongs to the script.

### Steps preamble

#### Standardizing argument handling

To avoid (re)structuring and destructuring data across function boundaries, we
are compelled to factor code into functions of many arguments. The context
required for each step (type) is not identical, although there is considerable
overlap. We standardize argument ordering to keep things manageable.

Argument order for step functions is as follows, with their reserved variable
names:

1. Script's own hash: `own_hash`
1. Tx constants:
1. Signatories : `signers = tx.extra_signatories`
1. Validity range lower bound `lb = tx.validity_range.lower_bound`,
1. Validity range upper bound `ub = tx.validity_range.upper_bound`
1. Mint derived: `n_burns`
1. Redeemer derived: `steps` / step specific variables
1. Input derived:
1. Total funds `tot_in`
1. Keys `keys_in`
1. Stage `stage_in`
1. Output derived (ordered analogously to input with `_out` suffix)

Not all steps require all context.

Note, it is to be confirmed whether the implementation will make use of currying
the `do_X` step functions.

The type of a bound in aiken is `IntervalBoundType`. Since this is a bit odd,
we'll use the alias `ExtendedInt`

### Do steps

We encode the step verification as function that fails or returns unit.

#### Do open

The logic of `open` is essentially covered by `new_output` and the `Mint` logic.
Since an `open` necessarily involves minting a thread token, we defer to the
`Mint` logic.

#### Do add

- One of `keys_in`, has signed the tx
- Total amount has increased by `x = tot_out - tot_in`, `x >= 0`
- Keys are unchanged (`keys_in == keys_out`)
- Expect `Opened(amt1_in, snapshot_in, period_in) = stage_in`
- Expect `Opened(amt1_out, snapshot_out, period_out) = stage_out`
- If the signer is `keys_in.0`, then `amt1_in == amt1_out` else
  `amt1_in + x == amt1_out`
- If `Some(snapshot) = maybe_snapshot` then
  - verify the `maybe_snapshot` with the other key
  - `snapshot_out` equals the union of `maybe_snapshot` and `snapshot_in`
- Else `snapshot_in == snapshout_out`

The function signature is

`fn do_add(   signers: List<VerificationKeyHash>,    maybe_snapshot: Option<Signed<Snapshot>>,    amt_in: Amount,    keys_in: Keys,    stage_in: Stage,    amt_out: Amount,    keys_out: Keys,    dat_out: Stage )`

#### Do close

- One of the `keys_in`, `closer`, has singed the tx
- `keys_out == (closer, non_closer)` where `non_closer` is the other key in
  `keys_in`
- Verify the `receipt` with key `non_closer`.
- The total funds is at least as much `tot_in <= tot_out`
- Unwrap the stages:
  - The `Opened(amt1, snapshot, respond_period) = stage_in`
  - The `Closed(amt, squash, timeout, pend) = stage_out`
- `amt` is a calculated by
  - the amount already recorded (either `tot_in - amt1` if the closer is also
    the open, else `amt1`)
  - plus the difference of squashes in the latest snapshot
  - plus the additional cheques not yet accounted for excluding pending cheques.
  - `squash` is the latest squash corresponding to the non-closer
  - `timout >= ub + respond_period`
  - `pend` is correctly derived from the receipt

No funds are removed.

Regardless of how large or small the `ub` or `timeout` is, the non-closer has at
least `respond_period` to perform a `respond`.  
If `timeout` is large, the closer is only postponing their ability to `elapse`
the channel were they to need to.

The tx size is in part linear in the number of cheques. Both partners must
ensure that the size of this transaction is sufficiently small to meet the L1 tx
limits. They must perform a `close` step before the number of cheques in their
possession exceeds these limits. If they do not, they put only their own funds
at risk - not their partners.

The signature of the do close function is

`fn do_close(   signers: List<VerificationKeyHash>,    ub: ExtendedInt,    receipt: Receipt,    amt_in: Amount,    keys_in: Keys,    stage_in: Stage,    amt_out: Amount,    keys_out: Keys,    dat_out: Stage )`

#### Do respond

The redeemer supplies the `(receipt, drop_old)`

- `keys_in.1` has singed the tx
- `keys_in == keys_out`
- Verify the receipt with `keys_in.0`
- Unwrap the stages:
  - The `Closed(amt, squash_in, timeout, pend) = stage_in`
  - The `Responded(amt_cont, pend0, pend1) = stage_out`
- `amt0` is a calculated by
  - the previous `amt0`
  - minus the difference of squashes if a newer snapshot is provided.
- if `drop_old` is true,
  - then `pend0` is `pend` with entries in which the `timeout < lb` have been
    dropped. The total reflects this
  - else `pend0 == pend`
- `pend1` is derived from the receipt for the responder.
- `tot_out` is equal to `tot_in`
  - minus `amt_cont` - owed to the closer
  - minus `pend0.0` - pending cheques of the closer
  - minus `pend1.0` - pending cheques of the responder

Both partners have now submitted their receipt as evidence of how much they are
owed from their off-chain transacting.

At this point the L1 has all the information as to how much both participants
are eligible to claim from the channel.

As with a close the tx size is linear in the number of cheques. Both partners
must ensure they would be able to `close` or `resolve` all their cheques,
without hitting tx limits.

#### Do elapse

- `keys_in.0` has singed the tx
- `keys_in == keys_out`
- Unwrap the stages:
  - The `Closed(amt, squash_in, timeout, pend) = stage_in`
  - The `Elapsed(pend_cont)`
- The respond period has passed (`timeout < lb`).
- If the secrets is empty, then `pend_cont == pend` and `amt_freed = 0`
- Else `pend_cont` is derived from `pend` dropping the freed entries, and
  `amt_freed` is the amount freed.
- `tot_out = tot_in - amt - amt_freed`.

The non-closer has failed to meet their obligation of providing their receipt.
The closer may now release their funds.

#### Do free

- `keys_in == keys_out`
- When `stage_in` is :

  - `Close(amt, squash, timeout, pend)`

    - `keys_in.0` has signed the tx.
    - `Close(amt_cont, squash, timeout, pend_cont) = stage_out`
    - `pend_cont` is reduced from `pend` using the secrets provided.
    - the total amount freed is `amt_freed`
    - `tot_out = tot_in
    - `amt_cont == amt + amt_freed`

  - `Responed(amt, pend0, pend1)`
    - `keys_in.1` has signed the tx.
    - `Resonded(amt_cont, pend0_cont, pend1_cont) = stage_out`
    - `amt_cont == amt`
    - if `drop_old` then `pend0_cont` is reduced from `pend0`.
    - `pend_cont` is reduced using the secrets provided.
    - the total amount freed is `amt_freed`
    - `tot_out = tot_in - amt_freed`
  - `Resolved(pend0, pend1)`

    - `Resolved(pend0_cont, pend1_cont) = stage_out`
    - If `keys_in.0` has signed the tx then
      - `pend0_cont` is `pend0` reduced with secrets,
      - if `drop_old` then
        - `pend0_cont` is `pend0` is reduced by `timeout < lb`,
    - Else:
      - `keys_in.1` has signed the tx.
      - the above logic with reduce methods switched.

  - `Elapsed(pend)` then:
    - `keys_in.0` has signed the tx.

Only the closer can `free` in the stages `Closed` and `Elapsed`. Only the
responder (non-closer) can `free` in the stage `Responded`. Both partners can
`free` in the `Resolved`.

#### Do end

- When `stage_in` is :
  - `Responed(amt, pend0, (0, []))`
    - All pending cheques are unlocked with secrets
    - `keys_in.0` has signed the tx.
  - `Resolved(pend0, pend1)`
    - All the pending cheques are dealt with, and the corresponding partner has
      signed the tx.
  - `Elapsed(pend)` then:
    - All pending cheques have timed out.
    - `keys_in.1` has signed the tx.

### Validator

#### Spend

Recall that All logic is deferred to the mint purpose.

- S.0 : Extract `own_hash = dat.0`.
- S.1 : Mint value `tx.mint` has `own_hash`

#### Mint

Broadly the mint logic is as follows:

- Count number of thread tokens minted and burned in own mint.
- If no thread tokens are minted or burned then a bolt token is used.
- If there are minted thread tokens, then the new outputs are in the outputs
  (and appear before all other script outputs)
- Extract from the tx the validity range and signatories.
- While there are steps:
  - Get next script input.
  - If step is not an `end`:
    - Get continuing output.
    - Do step specific verification.
  - If the step is an `end`, then:
    - Verify end step logic
    - Deduct one from the remaining burn total.
- Finally there are no more script inputs, and the remaining burn is 0.

The logic structure is informed by the fact that inputs are lexicographically
ordered, and that traversing lists should be minimized.

- When `red.0` is
  - `None`
    - Own mint value is either:
      - burn `tot_burns` of thread tokens
      - toggle one `bolt-token` (`tot_burns = 0`)
  - `Some(seed)`
    - `tx.inputs` includes `seed`
    - `own_mint` burns `tot_burns` thread tokens.
    - For each minted thread token in `own_mint`, the next output is a
      continuing output.
- `reduce(own_hash, signers, lb, ub, tot_burns, red.1, tx.inputs, tx.outputs)`

Note that in the case of minting thread tokens, we look for the seed in the
inputs independently of our main traversal. It is simpler to do this - the
alternative requires carrying around even more context.

It is recommended that the seed chosen is the lexicographically lowest output
reference. This is the cheapest and most efficient way to choose a seed. Once
the spending of the seed has been verified, the only inputs we care about are
those belonging to the script.

##### Reduce

The processing of steps is effectively performing a reduce on the `steps` and
`tx.inputs`.

```
fn reduce(
  own_hash : Bytearray,
  signers : List<Hash28>,
  lb : Bound,
  ub: Bound,
  n_burns: Int,
  steps : List<PStep>,
  inputs : List<Input>,
  outputs : List<Output>
)
```

- When `p_steps` is:
  - `[]` then finalize:
    - All end steps accounted for ie `n_burns == 0`
    - No remaining `inputs` belong to script (`no_inputs`)
  - `[p_step, ..rest_p_steps]` then:
    - Unpack next input
      `(cid, address, tot_int, keys_in, stage_in, rest_inputs) = next_input(own_hash, inputs)`
    - When `p_step` is:
      - `Continuing(step)` then:
        - Unpack continuing output
          `(tot_out, keys_out, stage_out, rest_outputs) = continuing_output(cid, address, outputs)`
        - when `step` is
          - `Add` then `do_add`
          - `Close` then `do_close`
          - `Respond` then `do_respond`
          - `Elapse` then `do_elapse`
          - `Free` then `do_free`
        - return `(n_burns, rest_outputs)`
      - `End(params) = step` then:
        - `do_end(signatories, maybe_free, stage_in, )`
        - return `(n_burns - 1, outputs)`
    - recur:
      `reduce( own_hash, signers, lb, ub, n_burns, rest_p_steps, rest_inputs, rest_outputs)`

## How to read this document

### Accessing data

A spend has an optional datum. Unless stated otherwise, we assume the datum does
exist. We refer to its value as `dat`.

All purposes have a redeemer, We refer to the value as `red`.

All purposes have a transaction object. We refer to this value as `tx`.

We use dot notation to access values. For example, the mint value in a tx is
`tx.mint`.

### Permissible shorthand

Variable names with suggestive names.

- `amt` - Amount
- `cid` - Channel Id
- `dat` - Datum
- `idx` - Index, of a cheque
- `mk_*` - Make \*
- `n_*` - 'number of \*'
- `red` - Redeemer
- `tot_*` - 'total of \*'
- `tx` - Transaction

Short hand should be used in cases where it is appropriate. All other shorthand
should only be used, at worst, in places where the scope is small and local.
