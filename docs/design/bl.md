# Bitcoin Lightning

Aims: explore the Bitcoin Lightning channel design, and how it may be informed
by the design, features, and constraints of Bitcoin. Particular focus is how
these design, features, and constraints are distinct with those of Cardano.

Non-aims: We do not consider at any other aspects of Lightning, such as routing
(beyond HTLC) or encodings.

## Blockchains

Cardano is heavily inspired by Bitcoin: It is utxo-based and (essentially)
longest chain consensus.

The motive of a Lightning style tool, that is orders of magnitude cheaper and
faster is shared by both chains. Bitcoin fees vary, but can be
<1$.  
Cardano fees are generally lower and much more predictable, often <.2$ .
Settlement times can vary on both chains, but are >10s.

Cardano has a much more powerful scripting language. This is likely the most
important distinction between the two chains with respect to our current focus.
TODO: compare Plutus and Bitcoin Script

There many other possible points of comparison such as proof of work vs stake.
However these are less relevant to our current focus.

## Sources

The Bitcoin Lighting spec is presented in
[Bolts](https://github.com/lightning/bolts). The Bolts of particular relevance
to us:

1. [peer protocol](https://github.com/lightning/bolts/blob/master/02-peer-protocol.md)
1. [on-chain](https://github.com/lightning/bolts/blob/master/05-onchain.md)

## Design

### The Lock

BL uses a 2-of-2 multisig script to lock funds on the Bitcoin ledger -
functionality supported in Bitcoin Script. The limited capabilities of Bitcoin
Script surely restricted the design choice available to lock funds.

A consequence of the locking mechanism is that much of the Lightning protocol
involves the passing of partially signed transactions. (Or at least the
signature of.) If one party wants to close the channel they can complete the
latest received (and valid) partially signed transaction with their own
signature, and publish (ie submit) this to the ledger.

By comparison, Plutus supports the capability on which a lock is based on the
signature of piece of data that may represent, say, the latest channel state.
The lock may also check the state against the channels history. Note: It is not
clear to the authors (due to their ignorance of the inner workings of Bitcoin
Script) whether such functionality exists, but it remains that the 2-of-2
mutlisig is used.

TODO: Clarify whether Bitcoin Script can do this.

### Funding

Funding seems ((FIXME: Check)) to happen once, in a single transaction and
requires Interactive Transaction Construction.

It may be interesting to consider funding channels in sequential transactions,
and whether this is a sufficiently helpful feature. For example, would it allow
a gateway to fund multiple channels in a single transaction (in a way that is
not dependent on any external party).

TODO:

### Slashing

TODO:

### No midlife fund reallocation

There is no mechanism in a channel to add or sub funds from a Channel.

It would be helpful in the application of, say, a Gateway to periodically
reallocate funds from channels with customers who own funds to channels with
merchants who are owed funds. And to do so without closing, and re-opening a
channel.

TODO: Check / Complete
