# Bitcoin Lightning Channel Design. What Can We Learn from It?

## 1. Introduction

### 1.1 Objectives

The Bitcoin Lightning Network (BLN) has emerged as a transformative solution for
scaling Bitcoin. It offers faster and more cost-effective transactions while
preserving core Bitcoin values—it is a decentralized and censorship-resistant
payment protocol. Payments on BLN are nearly instantly finalized, preserving the
full safety of the underlying blockchain.

Inspired by BLN, Cardano Lightning (CL) aims to implement similar advantages
within the Cardano ecosystem. However, rather than merely replicating BLN's
architecture, we seek to understand the underlying differences between the two
chains that can influence the final design of the CL channel.

It's important to note that our focus is strictly on channel design and channel
composition at this point. Aspects of the network like gossiping, routing
encryption, encoding, pathfinding, etc., fall outside the scope of this
discussion.

Besides the core channel design, we would like to understand how to preserve the
compatibility of the CL channels with BLN channels so a payment can be executed
across both blockchains in an atomic manner. We would like to also explore how
the blockchain properties and its derived ecosystem impacts the design,
operations, and implementations of channel management software (lightning nodes
and wallets).

### 1.2 Disclaimers

We are not experts in Bitcoin or BLN. All content is presented to the best of
our understanding. If you see any mistakes or have any suggestions, please let
us know on our GitHub issue tracker:
[https://github.com/cardano-lightning/cardano-lightning/issues](https://github.com/cardano-lightning/cardano-lightning/issues).

BLN is not a static project—it is under active development by several
independent entities. This makes it challenging to say with confidence "BLN
can't do X". For example, splicing—allowing for channel funds to be altered
midlife—did not exist in the original version of BLN but is now in the final
stages [^bln-splicing-pr].

Furthermore, saying "BLN can't do X due to the limitations of Bitcoin script and
L1" often joins more dots than the evidence supports. BLN accomplishes an
impressive amount often in ingenious and elegant ways, in the highly constrained
environment of Bitcoin script. We will take the liberty in places that it is
likely that choices were made because of the environment in which BLN operates.

## 2 BLN Channels 101

### 2.1 Overview

The Bitcoin Lightning Network (BLN) enables transactions that are significantly
faster and generally less expensive than those on the main Bitcoin ledger (Layer
1). While transaction fees on Bitcoin and Cardano fall usually under $1, BLN
typically charges fees that are less than 1% of the transaction amount and
offers nearly instant finality.

### 2.2 The Contract

BL uses a 2-of-2 multisig script to lock funds on the Bitcoin ledger -
functionality supported in Bitcoin Script. Bitcoin Script seems to have limited
capabilities regarding signature checking as the operations which perform
verfication do this only against the current transaction hash. The limited
capabilities of Bitcoin Script surely restricted the design choice available to
lock and represent transfer of funds.

A key aspect of the BLN protocol is the management of partially signed
commitment transactions. If a party wishes to close the channel, they can
finalize the most recent valid partially signed transaction with their signature
and then broadcast it to the blockchain.

Beyond these basic locking mechanisms, the commitment transaction includes more
complex scripts to facilitate revocations (penalties) and enable channel
composition using HTLCs
([Hashed Timelock Contracts](https://bitcoinwiki.org/wiki/hashed-timelock-contracts)).
To support channel composition, the protocol tracks not only the commitment
transaction but also any transactions associated with pending HTLCs'
[timeout or successful execution branches](https://github.com/lightning/bolts/blob/master/03-transactions.md#htlc-timeout-and-htlc-success-transactions).

By contrast, Plutus - Smart Contract Language on Cardano - offers enhanced
capabilities where locks can be based on the signature of any piece of data,
potentially representing the latest channel state. This allows for a more
streamlined representation of payments compared to the multiple chains of signed
transactions used in BLN. Plutus can also verify the state against the channel's
history, simplifying the overall complexity of managing state transitions.

## 3 Comparing Blockchains

Let's dive into a few attributes related to the core principles and rules which
govern both networks and try to identify how some of these differences can
impact lightning channels design and operations.

### 3.1 Consensus Protocol

Consensus is the mechanism by which a decentralised set of participants "agree"
what the true state is. It is fundamental to the security and functionality of
the blockchains.

Bitcoin uses a Proof-of-Work (PoW) algorithm with longest chain for consensus.

Cardano uses the Ouroboros Proof-of-Stake (PoS) consensus algorithm with an
augmented longest chain for consensus. The augmentation is to prevent _long
range_ attacks that PoS chains are more susceptible to.

#### 3.1.2 Transaction Finality

##### 3.1.2.1 Current Status

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

##### 3.1.2.2 Ouroboros Peras

Cardano is expecting a significant protocol upgrade with Ouroboros Peras, which
will introduce much faster finality for some block (thus all blocks beneeth
them) through [stake-based voting](https://peras.cardano-scaling.org/). This
feature heavily relies on the fact that we treat stake as a source of trust on
Cardano blockchain.

##### 3.1.2.3 Mempool and Congestion

Of course any congestion can affect the initial settlement time (when the
transaction is included in a lock) and influence the total time required from
the submission of the transaction to its finalization (when the transaction can
not be rolledback). The maximal throughput of both blockchains is currently in
the same ballpark.

##### 3.1.2.4 Implications

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
transaction.

We can of course enable more efficient execution strategies based on muti-sig
transactions and rely as BLN on a full off-chain consensus bewteen partners. As
we will learn in a moment this seemingly optimal multi-sig route can impose
inflexibility which can lead to actually more transactions in many contexts!

#### 3.1.3 Lightning Payment Finality

While the discussion above relates to Layer 1 (L1) finality, it's important to
note that once Lightning Channel is established payments exectued on that layer
achieve nearly instant payment finality. Successful payment paths ensure that
transactions are finalized predominantly by network speed.

#### 3.2 Data Availability and Lightweight Clients

##### 3.2.1 BLN "lightweight" clients

Blockchain data availability is crucial for the safety of the BLN channels. The
main channel UTxO's on-chain presence ensures that Layer 2 operations are secure
and can be settled on Layer 1 if necessary. Traditionally, BLN nodes rely on a
full Bitcoin node not only to settle or close channels but also to monitor Layer
1 for any potential security breaches. This dependency significantly impacts how
lightweight BLN trustless clients can truly be, affecting ease of installation,
use and adoption.

##### 3.2.2 Mithril

Cardano’s "stake-based trust" has enabled the creation of
[Mithril](https://mithril.network), a mechanism providing access to certified
blockchain snapshots generated on an six-hourly basis. These snapshots,
accessible via a
[REST API](https://mithril.network/doc/manual/developer-docs/nodes/mithril-client-library-wasm),
contain transaction information that can be trusted independently of the data
provider. This innovation will mark a significant advancement for
[lightweight wallets](https://github.com/input-output-hk/mithril/discussions/1273)
and potentially for Cardano Lightning (CL) clients as well. It allows for
channel liveness checks without direct access to a Cardano node and enables the
delegation of complex operations like channel settlement, closure, and splicing
to full nodes, which are then only verified by the client.

Furthermore, the synergy between CL and Mithril extends to economic
interactions, as Mithril data providers can utilize platforms like CL or
[subbit.xyz](https://subbit.xyz) to receive micro-payments for each API
response, fostering a sustainable model for data provision within the Cardano
ecosystem.

#### 3.3 Transaction Fees

Bitcoin transaction fees are dynamic, determined by a competitive fee market.
Transactions that offer higher fees are prioritized, filling blocks based on
willingness to pay.

Currently, transaction fees are generally lower on Cardano than on Bitcoin. Over
the past year, median fees on Bitcoin ranged from $0.2 to $20 USD, compared to
$0.08 to $0.17 USD on Cardano. This significant difference highlights the
distinct approaches each blockchain takes towards transaction selection but the
demand as well.

#### 3.3.1 Cardano's "(Un)Fairness" Dilemma

By default, Cardano nodes operate under a fairness principle, processing
transactions in the order they are received, regardless of the fee offered. This
model, although designed to be equitable, may not be sustainable as it could be
easily exploited, potentially leading to its replacement by
[some form of free-market fee system](https://iohk.io/en/research/library/papers/tiered-mechanisms-for-blockchain-transaction-fees/)
in the future.

This notion of "fairness" can be detrimental, particularly for users engaged in
time-sensitive contracts where delays result in financial losses. Unlike
Bitcoin, where users can increase fees to expedite transaction processing during
congestion, Cardano offers no such mechanism for prioritizing transactions based
on urgency.

#### 3.3.2 Fee Management in BLN

In the Bitcoin Lightning Network (BLN), managing transaction fees is crucial for
the efficient construction and exchange of multisig transactions. Fees are
negotiated at the channel's inception, adjusted throughout its lifecycle via the
`update_fee` message, and separately negotiated during dual closures.

For commitment or HTLC-related transactions, appropriate fee settings are vital.
Insufficient fees can delay or even block the settlement of these transactions.
For instance, if the fee for an HTLC success transaction is too low and the
counterparty is uncooperative, it could prevent the recipient from accessing the
settled funds, triggering the timeout branch instead.

This direct linkage of transaction fees to protocol operations introduces
certain risks and may necessitate additional operational costs to maintain
safety margins. Adjustments and renegotiations depend on active cooperation
between channel partners.

#### 3.3.3 Fee Decoupling

On Cardano, the CL protocol can abstract away from transaction-level
representations of channel state, allowing complete decoupling from transaction
fees. This capability will be of course limited to non-multisig protocol flows.
Unfortunately, the current fairness model limits the reliability of laveraging
that possible feature. Looking forward, this flexibility could allow liquidity
providers to manage risks more effectively, reducing the hazards associated with
large HTLCs.

While parts of the protocol that rely on multi-sig-based off-chain consensus may
face similar risks as those seen in Bitcoin, the key difference lies in the
ability to navigate around these risks without requiring partner cooperation,
thereby granting users greater control over their transaction fees.

### 3.4 Dust Limit

The concepts of Dust Limit and Min UTxO are crucial for understanding how small
amounts and the UTxOs that potentially carry them are managed within blockchain
networks such as Bitcoin and Cardano. Unlike traditional Layer 1 protocols,
Lightning as a Layer 2 protocol features a distinct fee model that potentially
enables micropayments.

#### 3.4.1 Bitcoin's Dust Limit

In Bitcoin, there is no official protocol rule that dictates the minimum amount
of BTC that must reside in a UTxO. The absence of such a limit poses a risk of
network spamming with very tiny UTxOs, which could increase the operational
costs for nodes. However, in practice, most nodes enforce a minimum BTC
limitation known as the Dust Limit, though it is not formally codified within
the protocol.

#### 3.4.2 Impact on Lightning Network

The Dust Limit significantly influences the design of the Lightning Network by
constraining how unresolved payments (HTLCs/PTLCs) are managed. These payments
are represented on the commitment transaction level as individual UTxOs because
there isn't a straightforward method to aggregate such small transactions into a
single UTxO without introducing excessive complexity. Consequently, partners
must accept that some of these microtransactions may be lost if they cannot be
settled back on the Layer 1 blockchain.

#### 3.4.3 Cardano's Approach

On Cardano, there is a protocol-level rule known as Min UTxO (or
[Minimum ADA](https://cardano-ledger.readthedocs.io/en/latest/explanations/min-utxo-mary.html)),
which functions similarly to Bitcoin's Dust Limit. Directly replicating the
Bitcoin Lightning Network (BLN) design could lead to similar issues with the
settlement of micropayments on Cardano. However, by not outputting HTLC UTxOs
and instead representing pending locked payments at the script state level for
processing through regular validation, we can nearly avoid these issues
entirely. This approach allows for the batching of tiny HTLCs, enhancing
processing efficiency. Nonetheless, there remains an economic threshold where
the fee for processing HTLC operations exceeds the value locked in them.
Ideally, users should have the option to bypass these payments when it's not
economically viable.

### 3.5 Non-Native Assets

Non-native assets are utilized across blockchain networks to represent
real-world assets or currencies through stablecoins. The Bitcoin network,
traditionally supporting only BTC, has seen significant developments with the
introduction of Taproot Assets, enhancing its layer one (L1) with multi-asset
capabilities. This addition, recently integrated into the Bitcoin Lightning
Network (BLN), supports "edge nodes" that facilitate payment routing across
channels with different types of coins, using swaps at clearly specified
exchange rates.

In contrast, non-native assets have built-in support on the Cardano blockchain,
which already hosts several operational stablecoins. This integration suggests
that including support for non-ADA channels could naturally fit into the core
design of the Cardano Lightning (CL) network. Moreover, the relative simplicity
and maturity of multi-asset capabilities on Cardano, compared to Bitcoin, could
significantly influence the adoption rate of this technology, as the presence of
stablecoins on-chain offers a robust foundation for expanding utility and user
engagement.

## 4. Smart Contract Languages

### 4.1 Characteristics

#### 4.1.1 The Scripting Power

Bitcoin and Cardano employ different smart contract languages: Bitcoin Script
and Plutus, respectively. These languages differ on two fundamental levels:

- **Computational Power**: Plutus is Turing complete, meaning that it can
  execute more complex computations, including loops and recursion. This
  capability allows for more elaborate program designs. However, the complexity
  of Turing-complete programs makes them more challenging to analyze. In
  contrast, Bitcoin Script is not Turing complete [^1], limiting its ability to
  perform such complex operations.

- **Operational Context**: The operational context in which validators function
  also varies significantly between the two. Bitcoin validators, which oversee
  the UTXOs, have limited access to transaction data and cannot maintain state
  information at the UTXO level. This restricts their ability to manage or
  verify state changes beyond simple transaction validations. Conversely,
  Cardano validators can access the entire transaction and its outputs, and they
  can store additional data with the UTXO. This capability enhances their
  ability to ensure accurate token distribution and supports ongoing operations
  within the network.

Additionally, it's important to note that the raw computational power of a smart
contract language, such as Turing completeness, often plays a limited role in
the practical applications within a blockchain context. Scripts are heavily
resource-bounded and typically operate over relatively simple transaction
structures that can be efficiently processed with built-in folds and maps. More
critical than sheer computational ability is the capability to access and
validate the entire transaction context—understanding the relationships and
dependencies across inputs and outputs. This capability significantly enhances
both the security and functionality of the network.

Cardano also offers Simple Scripts, which are comparatively less complex than
Bitcoin Scripts and are primarily used for straightforward multisig validations
and time-based logic. For the purpose of this discussion, we will concentrate on
the more complex aspects of smart contract functionality and not these simpler
scripts, considering multisig as an integral part of the transaction validation
process.

#### 4.1.2 The Script Responsibility

While Plutus's expansive capabilities offer significant advantages, they can
also introduce complexities that may not always be immediately beneficial:

- **Clarity of Script Responsibility**: In Bitcoin, the simplicity of Bitcoin
  Script makes it relatively straightforward to determine the limits of a
  script's responsibilities. This clarity aids in managing and understanding the
  security implications of each script. These inherent limitations often
  necessitate the off-chain exchange of transaction chains, maintaining
  simplicity in script logic.

- **Potential for Subtle Bugs**: On Cardano, the extensive functionalities
  enabled by Plutus can sometimes lead to subtle bugs or security
  vulnerabilities, such as
  [double satisfaction](https://library.mlabs.city/common-plutus-security-vulnerabilities#7.multiplesatisfaction)
  attacks. These vulnerabilities arise because the scripts can interact in
  complex ways, influenced by their ability to check a wide range of conditions
  and maintain states.

- **Operational Security and Verification**: In Bitcoin, it is generally clear
  that most of the verification burden and operational security of the protocol
  rely on the BLN nodes. In contrast, the complexity and broad capabilities of
  Plutus might give an impression that Cardano does not rely as heavily on
  similar security measures; however, this is not necessarily the case.
  Designing smart contracts on Cardano involves a delicate balance between
  safety guarantees, extensibility, and performance. It is crucial to be
  exceedingly precise when specifying what safety guarantees a script provides.
  This involves clearly defining the boundaries within which the script operates
  and the exact invariants it checks. Ambiguities in these specifications can
  lead to misunderstandings about the script’s security features and the
  responsibilities of L2 software.

### 4.2 Lightning Scripts

#### 4.2.1 BLN Contract

Within the constraints of the Bitcoin Script language, the BLN is characterized
by a multi-signature (two-party) output that locks channel funds. This output
awaits a transaction that will consume it and redistribute the funds according
to the channel's final state. Essentially, BLN shifts contract operations to
off-chain processing, where two parties exchange and update subsequent states
represented by Commitment Transactions that utilize the locked assets.

The UTXO representing the BLN channel is a straightforward multi-signature
output without an overseeing script. There are no scripts actively verifying
whether users are properly initiating or settling the channel based on
predefined rules. Instead, channel partners coordinate and validate the
transactions exchanged off-chain, agreeing by endorsing a new version with their
signatures.

In the BLN, scripts are primarily employed to prevent the submission of outdated
transactions/states or to manage the resolution of locked payments—HTLCs. To
handle these, BLN utilizes a series of pre-committed transactions; in addition
to the Commitment Transaction, partners exchange two separate transactions for
each
HTLC—[HTLC Timeout and HTLC Success Transactions](https://github.com/lightning/bolts/blob/master/03-transactions.md#htlc-timeout-and-htlc-success-transactions),
ensuring that funds can be reclaimed or successfully transferred based on the
outcome of the HTLC.

#### 4.2.2 CL Scripts and Multisig

On Cardano, we could adopt the BLN architecture and replicate the suite of BLN
scripts in Plutus. This approach would minimize resource use during each channel
validation step, though it may seem overly simplistic. Alternatively, leveraging
the full capabilities of Plutus allows for checking more invariants and
verifying signatures against arbitrary pieces of data, thus enabling a more
flexible protocol that abstracts away from direct transaction manipulation.

We could also blend both methods. Retaining a multi-sig option offers a quick
and cost-effective means to resolve channels. Concurrently, we might introduce a
more versatile approach in certain contexts that, while potentially increasing
L1 resource consumption, could ultimately result in more efficient time and
resource management overall.

#### 4.2.3 Operations

##### 4.2.3.1 Funding

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

On Cardano, channel funding can potentially be handled more flexibly. Starting
with single funding is simpler and might seem less efficient initially, but it
allows liquidity providers to add funds asynchronously later on, optimizing both
time and resources. These additional funding steps can be easily incorporated as
increases in liquidity are safe operations from the counterparty perspective and
are relatively easy to manage on the validator side. This straightforward
approach can prove to be efficient as it facilitates the batching of 'add'
operations by liquidity providers.

##### 4.2.3.2 Splicing

As of this writing, efforts are ongoing to enhance the BLN protocol by
[adding splicing support](https://github.com/lightning/bolts/pull/1160).
Splicing enables partners to add or remove funds from channels, necessitating an
L1 operation. This feature allows for the rebalancing of channel capacity
without the time and resource costs associated with closing and reopening
channels, which is particularly beneficial for liquidity providers.

In the BLN, both adding and removing funds involve the cooperative creation of a
multi-sig transaction, requiring active participation from both partners.
Theoretically, this process could be synchronized across multiple channels to
rebalance liquidity in a single transaction. However, implementing this in
practice can be challenging, especially in scenarios where edge nodes, such as
"customers," frequently transition between on-chain and off-chain states.

Conversely, Cardano Lightning could leverage its ability to handle arbitrary
data signatures to introduce a more adaptable approach. By using signed data as
permissions for partial fund adjustments, Cardano Lightning could facilitate a
more streamlined process. For instance, if a payment gateway accumulates
permissions from participating customers, it could execute fund adjustments in a
single transaction without the need for synchronous coordination typical of
multi-sig transaction setups.

This method would simplify channel management and enhance network flexibility,
taking full advantage of Cardano’s capabilities to verify signatures on
arbitrary pieces of data. Pursuing this approach could better accommodate the
dynamic nature of user participation and improve operational efficiency.

### 4.3 Penalty System - Design Choice or Imposed Limitation

#### 4.3.1 Overview of BLN's Penalty System

The penalty system in the Bitcoin Lightning Network (BLN) acts as a safeguard
against dishonest behaviors, specifically attempts to close the channel with an
outdated state. To deter such actions, both parties in a transaction associate
every historical transaction with a "revocation key." This key can penalize the
counterparty if they attempt to publish an outdated transaction. Additionally,
the protocol requires that a reserve amount be maintained at all times,
providing a financial disincentive against dishonesty. This system is often
justified through game-theoretical arguments, suggesting that the fear of losing
the reserve should theoretically deter fraud.

#### 4.3.2 Critique and Alternatives to the Penalty System

While effective in deterring fraud, the penalty system introduces significant
complexity and operational overhead. It necessitates the locking up of funds and
imposes additional storage requirements for revocation keys. These complexities
can be seen as adding unnecessary risk and burden to the participants.

##### Eltoo: A Simplified Update Mechanism

An emerging proposal called Eltoo represents a significant shift in handling
state updates within the Lightning Network. Eltoo proposes removing the penalty
system entirely, replacing it with a mechanism that allows on-chain settlement
updates. Under this system, if an old commitment transaction is submitted, the
counterparty has a window during which they can submit a newer state version.
This approach, requiring the new `SIGHASH_NOINPUT` signature flag (renamed to
[`SIGHASH_ANYPREVOUT`](https://github.com/bitcoin/bips/blob/master/bip-0118.mediawiki)),
simplifies the protocol by removing the need for penalties and reducing storage
requirements. However, it relies on capabilities not currently available in
Bitcoin script, such as a new opcode.

##### Benefits of Eltoo:

- **Reduced Storage Requirements**: Eliminates the need to store revocation
  secrets.
- **Symmetry of the Protocol**: Removes "toxic information," simplifying the
  operational complexity.
- **Scalability to More Participants**: The symmetric nature of the protocol
  makes it easier to extend to more participants.

#### 4.3.3 Cardano's Approach: Beyond Penalties

On Cardano Lightning, the unique capabilities of the platform could support an
alternative approach that avoids the traditional penalty system. Inspired by
mechanisms like Eltoo and Hydra, CL could allow for the direct overriding of
outdated states without imposing penalties. This method would simplify channel
management by eliminating the need for revocation keys and reducing operational
complexity.

##### Optional Penalty System:

Furthermore, CL could offer a hybrid approach where the penalty system is an
optional feature. Channel participants could choose to enable this feature if
they desire additional security layers, allowing for flexibility in how security
is managed based on the preferences and risk tolerance of the users involved.

### 5 Lightning Channels Composition

#### 5.1 HTLC

The implementation of Hashed Timelock Contracts (HTLCs) in the Bitcoin Lightning
Network (BLN) showcases an ingenious solution to overcome the network's
scripting limitations, facilitating secure and trustless multi-hop payments.
This system relies on a single cryptographic secret to unlock transactions,
demonstrating the robustness of Bitcoin's design approach. At its core, an HTLC
operates with just two variables: a `payment_secret` (the pre-image of a hash,
referred to as `payment_hash`) and a deadline for resolution, enabling the
atomic resolution of contracts based on the same secret. The protocol
implementation in BLN is complex, involving the construction of additional
transactions for each HTLC that might be used on Layer 1 during their
resolution. However, when resolved on Layer 2, these are merely consolidated and
removed from the channel state.

#### 5.2 Cross-Chain Payments

The cryptographic primitives involved in the composition of HTLCs are primarily
hashing functions. On the commitment transaction level, BLN employs its standard
double hashing technique, embedding the secret within the HTLC script as
`RIPEMD160(SHA256(secret))`. On the Cardano side, `RIPEMD160` is currently being
integrated
([CIP-0127](https://github.com/cardano-foundation/CIPs/tree/master/CIP-0127)),
but it is not necessary for these operations. Despite the double hashing on the
Bitcoin chain, parties within the Layer 2 protocol exchange using the SHA256
hash, which means that Cardano Lightning (CL) can adopt a compatible HTLC
locking mechanism with BLN. This compatibility facilitates the potential for
atomic swaps without additional bridges and supports cross-blockchain payments
using a design similar to
[Edge Nodes](https://docs.lightning.engineering/the-lightning-network/taproot-assets/edge-nodes),
enhancing interoperability across different blockchain platforms.

> This is still missing

## Conclusions

> This is still mess

## Sources

[^1]:
    Andreas M. Antonopoulos, "Mastering Bitcoin: Unlocking Digital
    Cryptocurrencies," 2nd edition, O'Reilly Media, 2017, p. 144.

The Bitcoin Lighting spec is presented in
[Bolts](https://github.com/lightning/bolts). The Bolts of particular relevance
to us:

1. [peer protocol](https://github.com/lightning/bolts/blob/master/02-peer-protocol.md)

[^bitcoinwiki-hashed-timelocks]:
    https://bitcoinwiki.org/wiki/hashed-timelock-contracts

[^bln-splicing-pr]:

[^bold-3-timeout-tx]:

[^subbit.xyz]:

[^tiered-fees]:
    https://iohk.io/en/blog/posts/2021/11/26/network-traffic-and-tiered-pricing/

1. [on-chain](https://github.com/lightning/bolts/blob/master/05-onchain.md)
   [^Eltoo] [^SIGHASH_ANYPREVOUT]
   https://github.com/bitcoin/bips/blob/master/bip-0118.mediawiki#user-content-Introduction
   [^Mastering Bitcoin] [^1]:
   [Taproot](https://bitcoinmagazine.com/technical/taproot-why-bitcoiners-are-so-excited-for-a-smarter-and-more-private-future)
   [^2]: [Mithril](
