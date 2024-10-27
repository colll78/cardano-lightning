# Bitcoin Lightning Channel Design. What Can We Learn from It?

## Introduction

The Bitcoin Lightning Network (BLN) has emerged as a transformative solution for scaling Bitcoin. It offers faster and more cost-effective transactions while preserving core Bitcoin values: decentralization and a safe, censorship-resistant payment protocol. Inspired by BLN, Cardano Lightning (CL) aims to implement similar advantages within the Cardano ecosystem. However, rather than merely replicating BLN's architecture, we seek to understand the underlying differences between the two chains that can influence the final design of CL channels.

It's important to note that our focus is strictly on channel design and channel composition. Aspects of the network like gossiping, routing encryption, encoding, pathfinding, etc., fall outside the scope of this discussion.

Furthermore, by no means are we Bitcoin experts, and we don't want to spread any misinformation. If you see any mistakes or have any suggestions, please let us know on our GitHub issue tracker: [https://github.com/cardano-lightning/cardano-lightning/issues](https://github.com/cardano-lightning/cardano-lightning/issues).

## Blockchains

> Key points:
> * Consensus:
>   * Bitcoin: PoW. It is hard to imagine solutions like Mithril which gives access to certified snapshots - safe sources of truth about the state of the blockchain.
>       * We want to possibly use this feature so the channel representation on L1 should be possibly easy to track or query through Mirhtril.
>       * BLN users have to either run both BLN node and Bitcoin node or **trust** a third party to provider.
>       * This is not the case on Cardano where we can have a certified snapshot of the chain so lighweight clients can exist.
>
>   * Another aspect which is somewhat related to the above point (threashold signatures) is the fact that on Cardano (with Peras) we will have much faster finalization on the chain (counted in minutes).
>       * Settlement time and finalization time hugely impacts the end user(s) experience buyers and sellers can both quickly plug into the network and start using it.
>       * This can also impact hugely liquidity providers and "robustness" of network because they possibly can quickly react to the demand of the channels and reallocate or increase capacity of the the channels.
>
> * Monoasset:
>   * Bitcoin is at its core monoasset at least that how BLN is designed.
>   * Cardano is multiasset by design.
>       * This can have huge implications for onboarding non-crypto retailers and users because they can not use stable coins on BLN at the moment.

### Consensus Protocol

Consensus mechanisms are fundamental to the security and functionality of blockchain networks. Bitcoin utilizes a Proof-of-Work (PoW) algorithm and Cardano employs the Ouroboros Proof-of-Stake (PoS) consensus algorithm. They achieve "similar" safety but measured using different resources - hashing power or amount of stake which belong to honest parties.

We can say that Cardano brings to the table a well defined finality treashold but it is currently so high (2160 blocks ~ 12 hours) that it seems still impractical. On both blockchains we can still rely on the probabilistic finality which is based of the block depth but in the case of Cardano which has much faster production rate we can achieve relatively high safety after just few minutes vs an hour on Bitcoin because blocks on cardano are produced every ~20 seconds and on Bitcoin every ~10 minutes.

Finality can affect how fast the lightning topology can be chanaged and how fast the channels can be considered open or closed. So the current parameters gives a bit of adventage to the Cardano blockchain.

On Cardano we have though With the new addition to the Ouroboros protocol we can expect that finality threashold to be significantly improved



### Throughput and Fees

We can say that the baseline throughput on both blockchains currently falls in to the same range (block production rate is different but size of the block compensates for that). Average transactions fees are significantly lower on Cardano but they probably won't stay on that level forever. Default Cardano node respects the fairness assumption (transactions are processed in the order they are received) we believe that this can easily be violated in the future and replaced with a free fee market. By analogy on Bitcoin there is a sequence number which by desing should be used to inform the miners which transactions version should be in the block. In practice this is not the case because the miners use the fee rate to prioritize the transactions.

The key take away is that both blockchains share similar limitations - they are realtively slow and their fees are relatively high so the transactions on L1 can not be used to process massive amount of microtransactions. This is the reason why the L2 solutions are needed. On the other hand both blockchains form a really solid and secure based for fast and efficient L2 payment solution like lightning.

TODO (paluh): Recheck the above fact about sequence number and the fairness of the Cardano protocol.

---

### Bitcoin Script vs Plutus

#### Scripting and validation - general discussion

> Key points:
> * Language power:
>   * Bitcoin Script is not Turing complete.
>   * Plutus is Turing complete.
>   * Surprisingly this difference is probably not critical because the environment in which the scripts are executed is really limited in both cases.
> * Validation capabilities:
>   * The set of basic operations in Bitcoin Script is limited:
>       * Signatures can be checked only against the current transaction hash.
>       * Access to the transaction is limited: no ability to look at the outputs.
>  * Plutus can do much more but this can be actually a disadvantage:
>   * In the case of Bitcoin it is easy to recognize where the possible responsibility of the script ends
>   * On Cardano it can lead to sometimes subtle bugs or security vulnerabilities like double satisfaction attacks.
>  * Thanks to its limitation Bitcoin Lightning utilizes a really simple and efficient way to encode the locks and the payments:
>   * The contract itself is expressed through exchange of multi-sig transactions with pretty easy to understand time locked or pre-image locked outputs which implement penalty mechanisms or HTLCs.
>   * This design is really efficient and allows to encode the whole channel state as a single multi-sig UTxO.
>   * The burden is on the implementators of the libraries and tools.
>  * On Cardano:
>   * We can implement more constraints on the validator side - the question is whether we want to do this or not. Using off-chain consensus can be more efficient and flexible so at least incorporating that into the BLN design as an option is worth considering.
>   * We can encode the channel state in much easier and concise way than transactions which possibly makes protocol easier to implement and understand.

### Funding

> * V1 contained only single funded channels
> * V2 adds ability for dual funding.
> * Question: why it took so long to implement this feature as it "only" changes the initial commitment transaction?
> * Answer: probably this is a proof that they are careful and also that some details in the context of multi-sig management can be tricky.
> * Cardano:
>   * because we can pretty naturally utilize multiple transactions for channel lifecycle we can start with "seemingly" inefficient approach which is single founding with the possibility to add more funds later.
>   * this design though simple can actually be really efficient because liquidity providers can batch `add` operations to optimize the time.
>   * this design is realatively simpler then upfront coordination of transaction creation across many parties.

### Splicing

> * Final sage of the design:
> * Flexibility:
>   * Multi-sig flexibility can be a bit limited because the trasnaction buidling has to be coordinated between the parties.
>   * Abstracting over the permission to perform fund removal on Cardano can introduce usability which is highly desired by the liquidity providers when extra asynchronicity is sometimes needed (some end users/customers can sporadically on-line).


### Penalty System - Design Choice or Imposed Limitation

> Key points:
> * BLN uses penalty system to enforce updates:
>   * Eltoo an different Bitcoin payment protocol proposal which uses "update" approach but it requires a new opcode.
>   * Cardano L2 solution Hydra uses simple overwriting mechanism (contestation) without penalty system.
>   * Penalty system adds some theoretical extra safety from game theory perspective.
>   * It introduces extra complexity because it requires reserve amount to be negotiated and funds to be locked.
>   * Penalty system imposes extra storage requirements on the channel participants as the revocation keys have to be stored.


-----

Loosely bullshit

There are two significant differnces between spending validators on Bitcoin and on Cardano:

* The languages differ regarding the computational power - Plutus is Turing complete but Bitcoin Script is not.
* What is also important is the difference between these validators execution contexts:
  * On Bitcoin we have limited access to the information contained in the transaction
  * On Cardano we can examine the whole transaction together with the outputs. This gives the validator ability to guarantee correct token distribution or its own continuation

A pretty amazing and surprising fact is that Bitcoin Lightning protocol shifts a lot of state validation to the offchain processing. In other words - it is not the script itself who checks whether users are progressing according to the rules but rather the users validate the transactions and either agree by providing signature under the new state or not.

Of course even on Cardano where scripts can check more invariants users still have to think and verify what are they signing but we can try to make it a bit harder to inroduce human or application programmer error.
On the other hand BLN proofs that making the transaction validation an external off-chain proess can be actually really efficient because the resource consumption on the chain is minimized.


------
Old version


### Consensus

Cardano is heavily inspired by Bitcoin: It is UTxO-based and (essentially) longest chain consensus. On the protocol leve core difference is that Cardano uses a proof of stake instead of proof of work which actually can impact hugely few aspects of L1 which is can have practical implications on the L2 experience.

: finalization time and information availability.


The motive of a Lightning style L2 solution, that is orders of magnitude cheaper and faster than L1 is shared by both chains.
Bitcoin fees vary, but can be <1$. Cardano fees are generally lower and much more predictable, often <.2$.


Finalization times can vary on both chains, but we can assume that they are larger than 10s.

## Design

### The Lock

BL uses a 2-of-2 multisig script to lock funds on the Bitcoin ledger -
functionality supported in Bitcoin Script.
The limited capabilities of Bitcoin Script surely restricted the design choice available to lock funds.

A consequence of the locking mechanism is that much of the Lightning protocol involves the passing of partially signed transactions. (Or at least the signature of.)
If one party wants to close the channel they can complete the latest received (and valid) partially signed transaction with their own signature, and publish (ie submit) this to the ledger.

By comparison, Plutus supports the capability on which a lock is based on the signature of piece of data that may represent, say, the latest channel state. The lock may also check the state against the channels history.
Note: It is not clear to the authors (due to their ignorance of the inner workings of Bitcoin Script)
whether such functionality exists, but it remains that the 2-of-2 mutlisig is used.

Bitcoin Script seems to have limited capabilities regarding signature checking as the operations which perform checking do this using the current transaction hash.

TODO: Clarify whether Bitcoin Script can do this.

### Funding

Funding seems ((FIXME: Check)) to happen once,
in a single transaction and requires Interactive Transaction Construction.

It may be interesting to consider funding channels in sequential transactions,
and whether this is a sufficiently helpful feature.
For example, would it allow a gateway to fund multiple channels
in a single transaction (in a way that is not dependent on any external party).

TODO:

### Splicing

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




## Sources

The Bitcoin Lighting spec is presented in [Bolts](https://github.com/lightning/bolts).
The Bolts of particular relevance to us:

1. [peer protocol](https://github.com/lightning/bolts/blob/master/02-peer-protocol.md)
1. [on-chain](https://github.com/lightning/bolts/blob/master/05-onchain.md)

