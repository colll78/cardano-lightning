Status: Draft; Early stage; Loose notes

Description: If and how channels should be identified on the chain.

# Channel Idetnification

## Channel identification - what is the purpose

* In the case of CL we can not rely on static UTxO to represent the channel uniquely because the channel could evolve and "move" to a different UTxO.

* Identifier allows information exchange between direct parties about state transition using a constant value.

* The on-chain code can use id to simplify the transition checks (output UTxO).

* Interaction with any other script which wants to access channel state information (probably the closing one) can be simplified though using current design it will be non trivial and require the other script inclusion in the final tx.


### Identification on the chain

As suggested above indentification of the channel insetance on the chain can be achived using different ways but it can require different client capabilites in order to use and verify it.

#### Different types of clients

We should probably consider at least the following types of clients:

    * Clients which have acceess to the full blockchain history or an interesting subset of it.

    * Clients which have access to some certified verification source like Mithril

    * Clients which have access to untrusted source of history but which can perform some verification using the certified source.

From CL protocol adoption perspective the more nodes can operate using the second or third model the better.


#### Different types of identification

We can use at least three approaches to identify channels:

    * No direct identifier - channel instance is associated with the initial UTxO and the client folds the contract thread. In order to operate safely:

        * Either requires full access an indexer which provides all the intermediate transactions and requires quering Mithril aggregator for all the transactions.

        * Or requires a trusted indexer so cardano node as well.

    * Identifier on the datum level. Proving:

        * Requires similar types of queries as the above which prove that the UTxO is really connected to the initial UTxO.

    * Identifier of the `Value` level which is minted using unique and safe policy. Proving:

        * Current Mithril API:

            * The last transaction body required from untrusted source.

            * Query to the existing Mithril transaction API (by hash) proves validity of that transaction and possibly past state of the channel.cardano

            * Combined with query about the recent certified block it can actually give short lived off-chain guarantees about the channel state.

        * Light wallet Mithril API (the latest Mithril design discussion: https://github.com/input-output-hk/mithril/discussions/1273):

            * Given known script address we can query the Mithril for the UTxOs at address which should be 

            * The above query can be really inefficient and return massive results (UTxOs for all the open channels). We can narrow the query by using unique staking part per channel.

## Thread Token

### Do we want it?

* It is hard to imagine direct incentiviced attack on a single channel when both parties know and track the exact state of the channel by performing L1 queries.

* It is probably more probable that some form of incentivized attack can be performed when we imagine payment operators - some security attacks can depend on confusion and weakness of the sofware behind it.


## Do we need it?

Clearly not. We could avoid any identification


## Main objectives

* Introduce unforgeable identifier on-chain.

* Introduce precondition checking on-chain.


## Main side effects

### Pros

* Simplify off-chain validity checks - single script hash determines `Value`, `Datum` and `Script` consistency. This can have an minimal impact on indexers performance.

* Removes ambiguity - uniquness is a guaranteed invariant. This simplifies not only indexers but other software as well.

* Simplify on-chain contract preservation checks (continuing UTxO identification) - useful in both singleton and batch mode.


### Cons

* Makes Hydra integration a bit harder. If we require presence of a unique token per channel then we could:

    * Mint a unique one based on randomness commitments (both parties provide signed hashes of "random" numbers)

    * We compute the final value from xoring the preimiges

    * We store the commitmets in the state

    * We use the commitments to recompute the token when performing the minting during the settlment of the channel on the L1 in the case when Hydra head is closed before the CL channel is closed.

## Design

* The same validator mints tokens and is used as channel validator (using `CIP-0069`).

* The same validator is be used for batching (rewarding) as well.

* Initial minting implements additional precondition checking of all the channel outputs (`UTxO` `Value` level vs `Datum`).

* Minting introduces token which can be :

    * Either based on the output UTxO and use its reference hash (`sha256(TxId <> Index)`). This hides the details about the original UTxO info which should be provided separately if needed.

    * It can kee the full `UTxO` reference: token name (max 32 bytes) could encode TxId (32 bytes) and amount of that token in the output could encode the index of the UTxO.

* Token in one form or the other is used as `ChannelId`.

* We can avoid redundancy on `Value` and `Datum` level and assume that channel `UTxO` can contain only three types of values:

    * Either `(min ADA`, Thread token, Channel asset)

    * or `(ADA, Thread token)` when `ADA` is the channel asset


* We guarnatee that token never leaks from the thread and that it is burned at during the closure.

## Self hash discovery

* Spending validator self hash discovery is costly `O(n)` where `n` is in the number of inputs.

* We discover self hash by "trusting" the thread token and avoid the cost.

* This is "unsafe" on the chain but safe from off-chain perspective because we ignore all non valid tokens right away.

* In the case of minting and batching (rewarding) we have `O(1)` self hash discovery.


## Pros

* Self preservation check We can use this to discover the self hash which will be used for self preservation cheqk

* Off-chain identification of only valid channels is trivial.

* Uniquness simplifies off-chain implementations - we have guaranteed


* Given the above presence of such a token uniquely identifies **only** valid channel and it can not be forged.

