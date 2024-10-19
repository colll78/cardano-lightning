# Bitcoin Lightning

Aims: explore the Bitcoin Lightning channel design,
and how it may be informed by the design, features, and constraints of Bitcoin.
Particular focus is how these design, features, and constraints
are distinct with those of Cardano.

Non-aims: We do not consider at any other aspects of Lightning,
such as routing (beyond HTLC) or encodings.

## Blockchains

Cardano is heavily inspired by Bitcoin:
It is utxo-based and (essentially) longest chain consensus.

The motive of a Lightning style tool, that is orders of magnitude cheaper and faster is shared by both chains.
Bitcoin fees vary, but can be <1$.  
Cardano fees are generally lower and much more predictable, often <.2$ .
Settlement times can vary on both chains, but are >10s.

Cardano has a much more powerful scripting language.
This is likely the most important distinction between the two chains
with respect to our current focus.

### Bitcoin Script vs Plutus
There are two significant differnces between spending validators on Bitcoin and on Cardano:

* The languages differ regarding the computational power - Plutus is Turing complete but Bitcoin Script is not.
* What is also important is the difference between these validators execution contexts:
  * On Bitcoin we have limited access to the information contained in the transaction
  * On Cardano we can examine the whole transaction together with the outputs. This gives the validator ability to guarantee correct token distribution or its own continuation

A pretty amazing and surprising fact is that Bitcoin Lightning protocol shifts a lot of state validation to the offchain processing. In other words - it is not the script itself who checks whether users are progressing according to the rules but rather the users validate the transactions and either agree by providing signature under the new state or not.
Of course even on Cardano where scripts can check more invariants users still have to think and verify what are they signing but we can try to make it a bit harder to inroduce human or application programmer error.
On the other hand BLN proofs that making the transaction validation an external off-chain proess can be actually really efficient because the resource consumption on the chain is minimized.


TODO: compare Plutus and Bitcoin Script

There many other possible points of comparison
such as proof of work vs stake.
However these are less relevant to our current focus.

## Sources

The Bitcoin Lighting spec is presented in [Bolts](https://github.com/lightning/bolts).
The Bolts of particular relevance to us:

1. [peer protocol](https://github.com/lightning/bolts/blob/master/02-peer-protocol.md)
1. [on-chain](https://github.com/lightning/bolts/blob/master/05-onchain.md)

## Design

### The Lock

BL uses a 2-of-2 multisig script to lock funds on the Bitcoin ledger -
functionality supported in Bitcoin Script.
The limited capabilities of Bitcoin Script surely restricted the design choice available to lock funds.

A consequence of the locking mechanism is that
much of the Lightning protocol involves the passing of partially signed transactions.
(Or at least the signature of.)
If one party wants to close the channel they can complete the
latest received (and valid) partially signed transaction with their own signature,
and publish (ie submit) this to the ledger.

By comparison, Plutus supports the capability on which a lock is based on
the signature of piece of data that may represent, say, the latest channel state.
The lock may also check the state against the channels history.
Note: It is not clear to the authors (due to their ignorance of the inner workings of Bitcoin Script)
whether such functionality exists, but it remains that the 2-of-2 mutlisig is used.

TODO: Clarify whether Bitcoin Script can do this.

### Funding

Funding seems ((FIXME: Check)) to happen once,
in a single transaction and requires Interactive Transaction Construction.

It may be interesting to consider funding channels in sequential transactions,
and whether this is a sufficiently helpful feature.
For example, would it allow a gateway to fund multiple channels
in a single transaction (in a way that is not dependent on any external party).

TODO:

### Slashing

TODO:

### No midlife fund reallocation

There is no mechanism in a channel to add or sub funds from a Channel.

It would be helpful in the application of, say, a Gateway
to periodically reallocate funds from channels with customers who own funds to channels with merchants who are owed funds.
And to do so without closing, and re-opening a channel.

TODO: Check / Complete

### HTLC
BLN uses really cool way to compose the channels and make payment accross them safe and atomic. This mechanism is called HTLC

Every lock is encoded as UTxO which is crazy optimal (483 UTxOs can be outputed)

Bitcoin encodes every payment which awaits confirmation (`payment_secret`) to release assets as UTxO. This represetnatation
