# Bitcoin Lightning Channel Design. What Can We Learn from It?

## 1. Introduction

### 1.1 Objectives

The Bitcoin Lightning Network (BLN) has emerged as a transformative solution for
scaling Bitcoin. It offers faster and more cost-effective transactions while
preserving core Bitcoin values - it is decentralized and censorship-resistant
payment protocol. Payments on BLN are near instantly finalized preserving the
full safety of the underlining blockchain.

Inspired by BLN, Cardano Lightning (CL) aims to implement similar advantages
within the Cardano ecosystem. However, rather than merely replicating BLN's
architecture, we seek to understand the underlying differences between the two
chains that can influence the final design of the CL channel.

It's important to note that our focus is strictly on channel design and channel
composition at this point. Aspects of the network like gossiping, routing
encryption, encoding, pathfinding, etc., fall outside the scope of this
discussion.

Beside the core channel design we would like to understand how to preserve
compatibility of the CL channels with BLN channels so a payment can be executed
across both blockchains in an atomic manner. We would like to also explore how
the blockchain properties and its derived ecosystem impacts the design and
operations and implementations of channel management software (lightning nodes
and wallets).

### 1.2 Disclaimers

We aren't Bitcoin nor BLN experts. All content is presented to the best of our
understanding. If you see any mistakes or have any suggestions, please let us
know on our GitHub issue tracker:
[https://github.com/cardano-lightning/cardano-lightning/issues](https://github.com/cardano-lightning/cardano-lightning/issues).

BLN is not a static project - it is under active development by several
independent entities. This makes it challenging to say with confidence "BLN
can't do X". For example splicing, allowing for channel funds to be altered
midlife, did not exist in the original version of BLN, but is being (has now
been?) implemented.

Furthermore, saying that "BLN can't do X because the limitations of Bitcoin
script and L1", is joining more dots than we often have the evidence to support.
BLN accomplishes an impressive amount often in ingenious and elegant ways, in
the highly constrained environment of Bitcoin script. We will take the liberty
in places that it is likely that choices we made _because_ of the environment in
which BLN operates.

> XXX: This section seem redundant - we should have full smart contract related
> section which dives deeper into multi-sig etc. On the other providing some
> details on how BLN channel works could be useful here.

## BLN Channels 101

BLN offers transactions that are orders of magnitude cheaper and faster than L1
is shared by both chains. Bitcoin fees vary, but can be <1$.

## The Contract

> TODO: Rephrase that to a general BLN contract overview. Originally This was in
> "# The Lock" section by @waalge

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

Bitcoin Script seems to have limited capabilities regarding signature checking
as the operations which perform checking do this using the current transaction
hash.

## Comparing Blockchains

Let's dive into a few attributes related to the core principles and rules which
govern both networks and try to identify how some of these differences can
impact lightning channels design and operations.

> Key points:
>
> - Consensus:
>
>   - Bitcoin: PoW. It is hard to imagine solutions like Mithril which gives
>     access to certified snapshots - safe sources of truth about the state of
>     the blockchain.
>     - We want to possibly use this feature so the channel representation on L1
>       should be possibly easy to track or query through Mirhtril.
>     - BLN users have to either run both BLN node and Bitcoin node or **trust**
>       a third party to provider.
>     - This is not the case on Cardano where we can have a certified snapshot
>       of the chain so lighweight clients can exist.
>   - Another aspect which is somewhat related to the above point (threashold
>     signatures) is the fact that on Cardano (with Peras) we will have much
>     faster finalization on the chain (counted in minutes).
>     - Settlement time and finalization time hugely impacts the end user(s)
>       experience buyers and sellers can both quickly plug into the network and
>       start using it.
>     - This can also impact hugely liquidity providers and "robustness" of
>       network because they possibly can quickly react to the demand of the
>       channels and reallocate or increase capacity of the the channels.
>
> - Monoasset:
>   - Bitcoin is at its core monoasset at least that how BLN is designed.
>   - Cardano is multiasset by design.
>     - This can have huge implications for onboarding non-crypto retailers and
>       users because they can not use stable coins on BLN at the moment.

### 3.1 Consensus Protocol

Consensus is the mechanism by which a decentralised set of participants "agree"
what the true state is. It is fundamental to the security and functionality of
the blockchains.

Bitcoin uses a Proof-of-Work (PoW) algorithm with longest chain for consensus.

Cardano uses the Ouroboros Proof-of-Stake (PoS) consensus algorithm with an
augmented longest chain for consensus. The augmentation is to prevent _long
range_ attacks that PoS chains are more susceptible to. It is much more similar
to that

#### 3.1.2 Finality

Bitcoin has only probabilistic finality. There is no limit to the size of a
rollback. However, the cost of creating a longer chain, triggering a rollback,
is exponential in the number of blocks. A block is produced roughly every 10
minutes.
[Kraken.com](https://support.kraken.com/hc/en-us/articles/203325283-Cryptocurrency-deposit-processing-times)
says it waits ~40 minutes, suggesting they wait for 3-4 blocks before
considering a transaction safely on-chain.

Cardano does have deterministic finality. It is currently high, 2160 blocks ~ 12
hours. Cardano also has probabilistic finality within this window, and in
practice rollbacks are rarely larger than a few blocks. A block is produced
roughly every 20-30 seconds.
[Kraken.com](https://support.kraken.com/hc/en-us/articles/203325283-Cryptocurrency-deposit-processing-times)
says it waits ~15 minutes, suggesting they wait for 45 blocks before considering
a transaction safely on-chain.

#### Mempool and congestion

every 10 minutes. Of course any congestion can affect the settlement time and
influence the total time required from the submission of the transaction to its
finalization. We should really understand that both blockchains maximal
throughput is currently in the same ballpark. On the other hand Cardano is
expecting a really significant protocol upgrade called Peras which through
"stake" based nature of that blockchain will add fast finality to it.

Finality and fees (discussed below) can affect how fast the lightning network
topology can be changed - how quickly channels can be opened and operational or
closed. It can also affect how smoothly the liquidity in that topology can be
adapted to the demands through operations like `splicing` which adds or removes
funds from the channel. Liquidity distribution across the topology is important
because it affects if and how big payment can be routed through the network
without the need for splitting and transferring it using much more involved
multi path payment.

Faster finality and cheaper transactions means that CL channels can possibly
utilize L1 with greater flexibility. At the baseline protocol level we probably
don't have to necessarily compresses every channel L1 operation into a single
transaction. We should of course possibly enable this more efficient strategy
based on muti-sig transactions - full off-chain consensus but as we will learn
these seemingly optimal route can impose inflexibility which can lead to
actually more transactions in many contexts!

#### 3.1.3 Data Availability and Lightweight Clients

### 3.2 Transaction Fees

Bitcoin transaction fees are dynamic and determined by a fee market. Blocks are
filled with the transactions willing to pay the highest fees.

This aspect is reflected in the BLN channel management as channel partners have
to establish together the fee value of their commitment transactions. For that
purpose we have `update_fee` message.

In the current market context transaction fees are lower on Cardano than on
Bitcoin (during the last year the median fees were in a 0.2 to 20 USD range vs
0.08 to 0.17 USD). Quite significant difference between those two blockchains is
how they currently approach transaction selection.

Default Cardano node respects the fairness assumption so when block is produced
transactions are processed in the order they were received regardless of the fee
amount. It is hard to believe that this model will be preserved (as it can be
pretty easily be violated) and not replaced by free fee market in the future.

### 3.3 Dust Limit

On the Bitcoin there is no protocol rule which directly manages the minimal
amount of BTC which should reside on a UTxO. Without such a limit there is a
risk of network spamming with really tiny UTxOs. This could could in turn
increase the cost of the nodes/network operations. In reallity though most of
the nodes impose such a min. BTC limitation through the "dust limit" - it is
just not formalized by the protocol. Nodes don't accept or propagate
transactions with too small UTxOs. This limit impacts the Lightning design and
limits where every unresolved payment (HTLC/PTLC) is represented on the
commitment transaction level as a UTxO because some pending microtransaction
can't be settled back on the L1 level. There is no way to group those easily
into a single UTxO (though it doesn't seem to be infeasible but probably
overcomplicated) and process in batch so partners have accept that some of such
payments can be lost. On Cardano we have protocol level rule which is called min
UTxO (or `min ADA`) which is similar in nature to the dust limit. We can
possibly inherit the problem if we directly copy the design. We could also "fix"
it by expecting that `min ADA` will be supplied separatelly but we can possibly
avoid this problem by handling HTLCs on the channel validator level. Instead of
outputing HTLC UTxO we can keep track of all the locked payments in the script
state and process them through regular validation. This gives us possibility of
batching tiny HTCLs etc. Of course e even in this context there is an economical
limit where when fee for HTLC processing operations is greater than the value
locked in it. Ideally users should be able to skip these payments.

### 3.4 Non Native Assets

> - Monoasset:
>   - Bitcoin is at its core monoasset at least that how BLN is designed.
>   - Cardano is multiasset by design.
>     - This can have huge implications for onboarding non-crypto retailers and
>       users because they can not use stable coins on BLN at the moment.

Non native assets are used accross blockchains to represent real-world assets or
currencies through stable coins. Bitcoin network natively does not support any
other tokens than BTC but there is really an interesting development around
Taproot Assets which adds multi asset support to that L1. This new multi-asset
capability was recently integrated into the BLN [^1]. A really interesting
aspect of that integration is that it supports "edge nodes" which can facilitate
payment routing across channels with different types of coins. It is done
through swapping with clearly specified exchange rate. Non native assets have
builtin support on Cardano blockchain and we already have a few operating stable
coins on the network. In this context it seems pretty natural that supporting
non ADA channels should be included into the core design of the CL.

## 4. Smart Contract Languages

> Key points:
>
> - Language power:
>   - Bitcoin Script is not Turing complete [^Mastering Bitcoin]
>   - Plutus is Turing complete.
>   - Surprisingly this difference is probably not critical because the
>     environment in which the scripts are executed is really limited in both
>     cases.
> - Validation capabilities:
>   - The set of basic operations in Bitcoin Script is limited:
>     - Signatures can be checked only against the current transaction hash.
>     - Access to the transaction is limited: no ability to look at the outputs.
> - Plutus can do much more but this can be actually a disadvantage:
> - In the case of Bitcoin it is easy to recognize where the possible
>   responsibility of the script ends
> - On Cardano it can lead to sometimes subtle bugs or security vulnerabilities
>   like double satisfaction attacks.
> - Thanks to its limitation Bitcoin Lightning utilizes a really simple and
>   efficient way to encode the locks and the payments:
> - The contract itself is expressed through exchange of multi-sig transactions
>   with pretty easy to understand time locked or pre-image locked outputs which
>   implement penalty mechanisms or HTLCs.
> - This design is really efficient and allows to encode the whole channel state
>   as a single multi-sig UTxO.
> - The burden is on the implementators of the libraries and tools.
> - On Cardano:
> - We can implement more constraints on the validator side - the question is
>   whether we want to do this or not. Using off-chain consensus can be more
>   efficient and flexible so at least incorporating that into the BLN design as
>   an option is worth considering.
> - We can encode the channel state in much easier and concise way than
>   transactions which possibly makes protocol easier to implement and
>   understand.

Bitcoin and Cardano use to different smart contract languages: Bitcoin Script
and Plutus respectively [^Note that Cardano has also native scripts]. They
differe on two levels:

- The computational power of these languages is different: Plutus is Turing
  complete but Bitcoin Script is not [^Mastering Bitcoin - 144]. Simplifying
  Turing completness means that the programs can be much more elaborate and use
  loops (or recursion). On the other hand such programs are much harder to
  analyze.

- The context in which validator operate is different. On Bitcoin validator
  which "guards" an UTxO have limited access to the information contained in the
  transaction and can not carry state on the UTxO level. On Cardano we can
  examine the whole transaction together with the outputs. Additionally we can
  store data attached to the UTxO. This gives the validator ability to guarantee
  correct token distribution or its own continuation.

### 4.1 Lighting Scripts

#### 4.1.1 BLN Contract

Given the constraints of the Bitcoin Script language BLN is represented by
multi-sig (two party) output which locks channel funds and awaits for a
transaction which consumes it and redistributes the money according to the final
state of that channel. In other words BLN moves the contract operation to the
off-chain procesing where two parties exchange and update subsequent versions
transaction(s) which consumes the locked assets.

The UTxO which represents the BLN channel is plain mutli-sig output so there is
no script which guards it. There is no script which checks whether users are
initiating or settling the channel according to the rules. Rather the channels
partners coordinate and validate the transactions exchanged off-chain and either
agree by providing signature under the new version of it or not. Scripts in the
context of BLN are utilized mostly to prevent old transaction/state submission
or to allow locked payments (HTLCs) resolution.

#### 4.1.2 CL Scripts and Multisig

For sure we could fully embrace the above architecture on Cardano and just
reimplement the set of small BLN scripts in Plutus. We can also try to utilize
the power of Plutus which allows us to check more invariants or verify
signatures under aribrary piece of data to implement a bit more flexible
protocol which abstracts away from direct transaction manipulation. Or we could
actually use both approaches. We could leave a multi-sig option for quick and
cheap resolution of the channel. Additionally we could provide different but in
may contexts more flexible wayt to manage the channel with necessarily would
directly involve some extra L1 resource consumption which at the end
surprisingly could facilitate less time and resource consumption.

#### 4.2 Operations

### 4.2.1 Funding

> Key points:
>
> - BLN "channel funding" history:
>   - V1 contained only single funded channels
>   - V2 adds ability for dual funding.
>   - Question: why it took so long to implement this feature as it "only"
>     changes the initial commitment transaction?
>   - Answer: probably this is a proof that they are careful and also that some
>     details in the context of multi-sig management can be tricky.
> - Cardano:
>   - because we can pretty naturally utilize multiple transactions for channel
>     lifecycle we can start with "seemingly" inefficient approach which is
>     single founding with the possibility to add more funds later.
>   - this design though simple can actually be really efficient because
>     liquidity providers can batch `add` operations to optimize the time.
>     Additionally this process can be asynchronous.
>   - this design is realatively simpler then upfront coordination of
>     transaction creation across many parties.

Initially, the BLN only supported single-funded channels which were much easier
to implement. Funding transaction which creates the channel through multi-sig
channel UTxO and requires only funder signature. This transaction can be settled
once the funder receives signed refund transaction which secures the initial
channel balances. A later version of BLN peer protocol introduced dual funding,
which allows both parties to contribute the initial funds. This development was
relatively slow because it required careful design of interactive transaction
buildup of that funding multi-sig transaction. This interative protocol
constructs transaction piece by piece by adding single outputs and inputs from
both partners. Actually even more lighting users can be involved in this buildup
to coordinate funding of multiple channels at the same time.

Cardano can potentially handle channel funding more flexibly. Starting with
single funding is simpler and may seem inefficient, but it allows liquidity
providers to add funds asynchronously later on, optimizing both time and
resources. This approach, while straightforward, can prove efficient as it
allows batching of 'add' operations by liquidity providers.

### 4.2.2 Splicing

> Key points:
>
> - BLN still lacks it though the addition is in the final stage.
> - Multi-sig flexibility can be a bit limited because the trasnaction buidling
>   has to be coordinated between the parties.
> - Abstracting over the permission to perform fund removal on Cardano can
>   introduce usability which is highly desired by the liquidity providers when
>   extra asynchronicity is sometimes needed (some end users/customers are
>   sporadically on-line).

### 4.3 Penalty System - Design Choice or Imposed Limitation

> Key points:
>
> - BLN uses penalty system to enforce updates:
>   - Eltoo an different Bitcoin payment protocol proposal which uses "update"
>     approach but it requires a new opcode.
>   - Cardano L2 solution Hydra uses simple overwriting mechanism (contestation)
>     without penalty system.
>   - Penalty system adds some theoretical extra safety from game theory
>     perspective.
>   - It introduces extra complexity because it requires reserve amount to be
>     negotiated and funds to be locked.
>   - Penalty system imposes extra storage requirements on the channel
>     participants as the revocation keys have to be stored.

### HTLC and Crosschain Composition

> Key points:
>
> - We have all the crypto primitives:
>   - BLN uses RIPEMD160 but only on the chain (Plutus will have it) - peer
>     protocol exchanges the lock in the form of sha256
> - PTLC:
>   - Operationally it is "rather simple":
>     - It uses linear nature of the Schnorr scheme - when we "add secrets" the
>       results of the hard to reverse function ("hash") also add up.
>   - It is still under discussion [^I have useful link] and the AFAIU the last
>     design required only Schnorr signatures which we have on Cardano.
>   - Should adopt it right away in CL? We shouldn't because it complicates flow
>     and it is outside of the current phase of the project.

## Sources

The Bitcoin Lighting spec is presented in
[Bolts](https://github.com/lightning/bolts). The Bolts of particular relevance
to us:

1. [peer protocol](https://github.com/lightning/bolts/blob/master/02-peer-protocol.md)
1. [on-chain](https://github.com/lightning/bolts/blob/master/05-onchain.md)
