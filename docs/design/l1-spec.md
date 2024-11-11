---
title: CL L1 Spec
author:
  - "@waalge"
  - "@paluh"
---

## Intro

Cardano Lightning (CL) is p2p payment solution inspired by Bitcoin Lightning
Network, and built over the Cardano blockchain. It is an L2 optimized for:

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

### Steps and stages

CL consists of a single Plutus V3 validator executed in both `Mint` and `Spend`
purpose.

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

### Data

#### Cheques

Cheques a vehicle through wish funds are sent from one partner to the other. As
such they must be understood on the L1.

```aiken
type Index = Int
type Amount = Int
type Expiry = Int // Posix Timestamp

type Normal = (Index, Amount)

type Hash32 = ByteString -- 32 bytes

type Lock {
  Blake2b256Lock(Hash32)
  Sha2256Lock(Hash32)
  Sha3256Lock(Hash32)
}

type Locked {
  Htlc(Index, Amount, Expiry, Lock)
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
type Signed<T> = Signed(T, Signature)
```

#### Snapshot

```aiken
type Exclude = List<Index>
type Squash = (Amount, Index, Exclude)
type Snapshot = (Squash, Squash)
```

#### Receipt

```aiken
type Receipt =  (Option<Signed<Snapshot>>, List<Signed<MCheque>>)
```

#### Datum

```aiken
type ScriptHash = ByteArray // 28 bytes
type VerificationKey = ByteString // 32 bytes,
type Keys = (VerificationKey, VerificationKey)
type Pend = (Amount, List<ChequeReduced>)
type Period = Int // Time delta

type Stage {
  Opened(Amount, Snapshot, Period)
  Closed(Amount, Squash, Expiry, Pend)
  Responded(Amount, Pend, Pend)
  Resolved(Pend, Pend)
  Elapsed(Pend)
}

type Datum = (ScriptHash, Keys, Stage)
```

#### Redeemer

```aiken
type Redeemer = (Option<OutputReference>, List<Step>)

type Step {
  // Open is dealt with separately cos there's no input
  Add
  Close(Receipt)
  Respond(Receipt, Bool) // Walk over your list, remove expired locked cheques
  Resolve
  Elapse(List<Free>)
  Free
  End
}

```

## Constants

```ini
max_pend = 20
```

### Logic

All logic is deferred to the mint purpose.

#### Spend

- S.0 : Extract `own_hash = dat.0`.
- S.1 : Mint value `tx.mint` has `own_hash`

#### Mint

Broadly the logic is follows:

- Count number of thread tokens minted and burned in own mint.
- If no thread tokens are minted or burned then a bolt token is used.
- If there new thread tokens, then continuing outputs are first block of
  outputs.
- Extract from the tx the validity range and signatories.
- While there are steps:
  - Get next script input.
  - Extract the stage and total funds amount.
  - If the step is an `end`, then we deduct from the remaining burn total.
  - Else the next output is the corresponding output. Extract the continuing
    stage and amount.
  - Do step specific verification steps.
- Finally there are no more script inputs or steps, and the remaining burn total
  is 0.

The logic structure is informed by the fact that inputs are lexicographically
ordered, and that traversing lists should be minimized.

We recursively call the `next` which methodically works its way through the
`red.1`, `tx.inputs`, and `tx.outputs`.

- Z : Extract `own_mint` from `tx.mint`
- Z : Count `(n_burns, n_mints)` of thread tokens (ignore `bolt-tokens`).
- Z : If `red.0` is `Some(seed)` then `tx.inputs` includes `seed`.
- Z : Else `n_mints` is `0`.
- Z : If `red.0`, first `n_mints` inputs are opens.

- M.0 : if `red.0` is
  - M.0.0 : `None`
    - M.0.0.0 : own mint value is either burn `n_burns` thread tokens or mint or
      burn one `bolt-token` (`n_burns == 0`)
  - M.0.1 : `Some(seed)`
    - M.0.1.0 : `tx.inputs` includes `seed`
    - M.0.1.1 : `own_mint` burns `n_burns` thread tokens.
    - M.0.1.2 : For each minted thread token in `own_mint`, the next output is a
      continuing output.
- M.1 : `do_step(red.1, tx.inputs, tx.outputs, n_burns)`

Note. Choose the seed to be the lexicographically lowest output reference to
make this cheap. Because we've already dealt with the only input we care about
that isn't a script input, we can filter inputs that aren't own address.

Next input. The next input function

```
fn next_input(own_cred : Credentials, inputs : List<Input>) -> (cid, address, amount, keys, stage, inputs) {
  when inputs is {
    [input, ..rest] -> { if Output {} }
  }
}
fn next_output(cid : ChannelId, address : Address, outputs : List<Output>) -> (amount, keys, stage, rest) {
  when inputs is {
    [input, ..rest] -> { if Output {} }
  }
}
```

##### Step preamble

All steps, except `open` require exactly one input. An `open` requires none. All
steps that are not an `end` require a (single) continuing output.

###### New input

A new output is determined by the `seed` and (relative) output index.

`cid = mk_cid(seed, idx)`

**New output**. Similar to `get_cont`.

- Address has payment credentials of own script.
- Value is thread token with channel id `cid` and either:
  - ada
  - ada and channel currency
- Datum is inlined, and has correct `dat.0` own hash.

Note that staking credentials are up to the opener, and are set for the
channel's life.

There are no return values. Thus the signature is

`fn new_output(own_hash: ScriptHash, cid : ChannelId, outputs : List<Output>) -> ()`

No checks are done since only the funds at risk are those belonging to the
submitter of the tx. The non-opener must check the state of the channel before
participating.

###### Next input

A next input function finds the next input with payment credentials matching own
credentials. If yes, the function further destructures the input, else it
recurses with the tail of inputs. It the list of inputs is empty, the function
fails.

The input must have a thread token, and the `cid` is extracted. The amount of
the channel currency `total_amount` is extracted. The datum is destructured The
`dat.0` is not verified (it is necessary to check for the output, not input).

Thus the function signature is

```aiken
fn next_input(own_cred : Credentials, inputs : List<Input>) -> (cid, address, amount, keys, stage, inputs)
```

###### Continuing output

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

###### Arg ordering

To avoid (re)structuring and destructuring data across function boundaries, we
are compelled to factor code into functions of many arguments. We standardize
argument ordering to keep things manageable

Argument order for step functions

1. Tx constants (such as tx signatories and validity range)
2. Channel specific
   1. From the redeemer, where required
   2. From the input
   3. From the output, where continuing

For the input or output the ordering is

1. Address derived
2. Value derived
3. Datum derived

All steps have the ultimate set of arguments:

- `amt_in`, `keys_in`, `stage_in`

All continuing steps have penultimate set of arguments:

- `amt_out, keys_out, stage_out`

The first set of arguments of any step are then:

FIXME...

##### Steps

The processing of steps is coordinated by a function `do_step`.

```
fn do_step(
  signers : List<Hash28>,
  lb : Bound,
  ub: Bound,
  n_burns: Int,
  steps : List<Steps>,
  inputs : List<Input>,
  outputs : List<Output>
)
```

- X.0 : When `steps` is
- X.0.0 : `[step, ..rest]` then match `step`
  - `Close(receipt)` then `do_close(receipt, rest, n_burns, inputs, outputs)`
- X.0.1 : Otherwise finalize
  - X.0.1.0 : all terminal steps `n_burns == 0`
  - X.0.1.1 : no `inputs` belong to script

###### Open

###### Add

- One of `keys_in` has signed the tx
- The total amount has increased by `x`.
- If the signer is `keys_in.1`, then the amount in the datum is increased by
  `x`.

`fn do_add(signers, amt_in, keys_in, stage_in, amt_out, keys_out, dat_out)`

###### Close

- One of the `keys_in`, `closer`, has singed the tx
- `keys_out = (closed, non_closer)` where `non_closer` is the other key
- Verify the receipt with key `non_closer`.

`fn do_add(ub, receipt, amt_in, keys_in, stage_in, amt_out, keys_out, dat_out)`

All content of the receipt is signed by `non_closer`

- X.add.0 : `(input, rest_inputs) = get_own_input(inputs)`
- X.add.1 : Input stage is `Opened(amt, snapshot)`
- X.add.1 : `[output, ..rest_outputs] = outputs`
- X.add.1

#### Shared

Verifying a receipt `receipt` with `key`:

###### Close

`fn do_close(receipt : Receipt, steps : List<Steps> ,  n_burns: Int, inputs : List<Input>, outputs : List<Output>) `

- X.1.0 : `(input, rest_inputs) = get_own_input(inputs)`
- X.1.1 : Input stage is `Opened(amt, snapshot)`
- X.1.1 : `[output, ..rest_outputs] = outputs`
- X.1.1

### Txs

## How to read this document

### Accessing data

A spend has an optional datum. Unless stated otherwise, we assume the datum does
exist. We refer to its value as `dat`.

All purposes have a redeemer, We refer to the value as `red`.

All purposes have a transaction object. We refer to this value as `tx`.

We use dot notation to access values. For example, the mint value in a tx is
`tx.mint`.

### Permissible shorthand

- `amt` - Amount
- `cid` - Channel ID
- `idx` - Index
- `mk_*` - Make
- `n_*` - 'number of'

- `tx` - Transaction

=================================================

## Validator

The dapp consists of a single validator.

### Constraints

- Purpose is Spend (`own_oref`).
- Extract own datum as `Dat { fix : prev_fix, var : prev }`.
- Extract own value `prev_val`. Exclusively ada
- If `Cont red_ idx = Redeemer` then
  - Extract `next_output = outputs[idx]`
  - Address is own address
  - Value is `next_val`. Exclusively ada
  - Parse `next_output` datum as `Dat { fix : next_fix, var : next }`
  - `prev_fix == next_fix`.
- Else is terminal `red` is `Drain`

When `(prev, red_, next)` is

`(Ready, Join, Open(open))`:

1. Counter party signed tx ie `extra_signatories |> includes(prev_fix.pk1)`.
2. Counter party funds account `acc1 = next_val - prev_val >= 0`
3. `next` has "default" state ie
   `open = OpenParams 0 0 0 (Snapshot 0 prev_val [] acc0 [])`

`(Open(OpenParams pd pa0 pa1 ps), Add, Open(OpenParams nd na0 na1 ns))`:

1. Snapshot and delta are unchanged: `ps == ns` and `pd == nd`
2. Ada added: `amt = next_val - prev_val >= MIN_ADD`
3. Accounts have increased:
   `pa0 >= na0 && pa1 >= na1 && (pa0 + pa1) + amt == (na0 + na1)`

`(Open(OpenParams pd pa0 pa1 ps), Sub cs, Open(OpenParams nd na0 na1 ns))`:

1. TODO

`(Open(OpenParams pd pa0 pa1 ps), Close cs signedCheques, Closed(ClosedParams nd na0 na1 ns))`:

1. TODO : Need to track who closes

`(Closed(ClosedParams pd pa0 pa1 ps), Counter cs signedCheques, Done)`:

1. TODO

Terminal case:

If `prev` is `Ready`:

1. Tx is signed by `dat.fix.pk0`.

If `prev` is `Closed`:

1. TODO

## Functions

### Coercion to bytes

All data has canonical serialization. TODO: Clarify this point.

```haskell
asBytes :: x serializable; x -> ByteString
asBytes x = x
```

### Unlocking

The protocol supports all hashing schemes available in Plutus.

A limit is placed on the size of the secret `preimg`. This is to prevent a
scenario where a `preimg` is so large it could cause tx size issues.

```haskell
unlocks :: Secret -> Hash32 -> Bool
unlocks preimg lock = (img == lock) && (length preimg =< 64)
  where
    img = case lock of
      | Blake2b256Lock h -> blake2b_256 preimg
      | Sha2256Lock h -> sha2_256 preimg
      | Sha2256Lock h -> sha3_256 preimg
```

TODO : Does this need to be set to 32 to align with
https://gist.github.com/markblundeberg/7a932c98179de2190049f5823907c016

### Verify

The protocol supports all signature schemes available in Plutus.

```haskell
-- Should this be sha256? sometimes?
hash :: ByteString -> Hash
hash msg =
  if (length msg == 32)
    then return msg
    else return blake2b_256 msg

verify :: PubKey -> ByteString -> Signature -> Bool
verify pubkey msg signature = case signature of
  | Ed25519Signature sig -> verifyEd25519Signature pubkey msg sig
  | EcdsaSecp256k1Signature sig -> verifyEcdsaSecp256k1Signature pubkey (hash msg) sig
  | SchnorrSecp256k1Signature sig -> verifySchnorrSecp256k1Signature pubkey msg sig
```

Messages are prepended with the `ChannelId` as the effective nonce. All messages
for a given channel have some cumulative element (eg Cheques have and `Index`
and/or `Amount`) preventing reuse.

Cheques

```haskell
verifyCheque channelId pubkey signedCheque = case signedCheque of
  | SignedNormalCheque cheque signature -> verify pubkey (concat channelId $ asBytes cheque) signature
  | SignedLockedCheque cheque signature ->
      (verify pubkey (concat channelId $ asBytes cheque) signature) &&
      ((cheque ^. secret) `unlocks` lock)
```

Snapshots

```haskell
verifySnapshot channelId signedSnapshot pk0 pk1 =
    (verify' pk0 sig0) && (verify' pk1 sig1)
  where
    SignedSnapshot snapshot sig0 sig1 = signedSnapshot
    verify' pk sig = verify pk (concat channelId $ asBytes snapshot) sig
```
