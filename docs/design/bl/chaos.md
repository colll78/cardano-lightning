#CHAOS

# Bitcoin Lightning

Aims: explore the Bitcoin Lightning channel design, and how it may be informed by the design, features, and constraints of Bitcoin.
Particular focus is how these design, features, and constraints are distinct with those of Cardano.

Non-aims: We do not consider at any other aspects of Lightning, such as routing (beyond HTLC) or encodings.

## Key Points

* Power of scripting languages and general requirments

* Simple Scripts on Cardano vs Bitcoin Scripts:

    * No Hashing which is required for Revocation

        https://github.com/input-output-hk/cardano-node-wiki/blob/main/docs/reference/simple-scripts.md

        ```
        <script> ::= <RequireSignature>  <vkeyhash>
                   | <RequireTimeBefore> <slotno>
                   | <RequireTimeAfter>  <slotno>

                   | <RequireAllOf>     <script>*
                   | <RequireAnyOf>     <script>*
                   | <RequireMOf> <num> <script>*
        ```

* Plutus is much more stronger than Bitcoin Script.

* A slight complication from using Plutus for locking HTLC and revocation UTxO - collateral required.

* Interactive negotiation protocol - dual funding:

    * Bitcoin locking happens directly on the chain

    * We can solve it using CIP-0069 and preliminary validation - commitment on the data level.

                                                     Change UTxO
                                              ╭──────────────────────
                                              │
                  ╭─────────────────────╮     │
                  │                     │     │
                  │                     ├─────╯
──────────────────┤     Funding Tx      │
                  │                     ├─────╮
                  │                     │     │
                  ╰─────────────────────╯     │
                                              │
                                              │
                                              │           To: Channel 2 of 2
                                              ╰────────── Of: 2 BTC──────



Eltoo:

Layer 2 protocols are a form of smart contracts between a fixed set of
participants, that negotiate contract state changes locally, only involving the
blockchain in case of dispute or final contract settlement. These protocols
commonly consist of a *setup phase*, a *negotiation phase* and a *settlement
phase*. The setup phase involves moving some funds into an address con-
trolled by all participants, such that the participants have to agree on how
to distribute the funds later. The negotiation phase is the core of the pro-
tocols and consists of repeated adjustments on the distribution of funds to
participants. Finally, the settlement phase simply enforces the agreed upon
distribution on the blockchain.

5.2 Extending the protocol to more parties

As mentioned above the storage requirements for participants consist of the
latest tuple of update and settlement transaction. This is because they can
be rebound to any of the intermediate update transactions in case it gets
broadcast. This is in stark contract to the Lightning Network, where the
reaction to a previous state being published needs to tailored to that specific
state.
In Lightning the information stored is asymmetric, i.e., the information
stored by one endpoint is different from the information stored by the other.
In fact the security of Lightning hinges on the information being kept private
since publishing it could result in the funds being claimed by the other
endpoint. We refer to this information about previous states as being toxic.
With eltoo the information stored by the participants is symmetric, elimi-
nating the toxic information, and greatly simplifying the protocol as a whole.
The information being symmetric also enables extending the protocol to any
number of participants, since there is no longer a combinatorial problem of
how to react to a specific participant misbehaving.
The protocol can be generalized to any number of participants by simply
gathering all the settlement and update public keys of the participants and
listing them in the public key list. Due to the size constraints imposed on
17the output scripts it is currently not possible to go beyond 7 participants.
This results from each participant contributing 2 public keys, 33 bytes each,
and the script size for P2SH scripts being limited to 520 bytes.
This limit is raised to 10’000 bytes for P2WSH scripts, allowing up to
150 participants, but producing very costly on-chain transactions. However,
with the introduction of schnorr signatures, and aggregatable signature it is
possible to extend this to any number of participants, and without incurring
the on-chain cost, since all public keys and signatures are aggregated into a
single public key and a single signature.
6
Related Work
The invalidation problem of superceded states is central to the all layer 2
protocols, and a number of proposals have been proposed. The idea of rene-
gotiating transactions while they are still unconfirmed dates back to the orig-
inal design Bitcoin by Nakamoto. This original design aimed to use sequence
numbers in the transactions to allow replacing superseded transactions sim-
ply by incrementing the sequence number. Miners were supposed to replace
any transaction in their memory pool by transactions with higher sequence
numbers. However, this mechanism was flawed since a rational miner will
always prefer transactions with a higher expected payout, even though they
may have a lower sequence number. An attacker could incentivize miners to
confirm a specific version by adding fees either publicly or by directly bribing
the miners.
A first invalidation mechanism that was actually deployed was used by
the simple micropayment channels by Hearn and Spilman [6]. The simple
micropayment channel supports incremental transfer of value in only one
direction, from a sender to a recipient. It uses partially signed transactions
that can be completed only by the recipient, which will only ever enforce the
latest state since it is the state that maximizes its payout. The unidirectional
nature of the simple micropayment channels severely limit their utility as
they can only be used for incremental payments and, once the funds in a
channel are exhausted, the channel has to be settled on-chain, and a new
one has to be set up.
The Lightning Network, proposed by Joseph Poon and Thaddeus Dryja [7]
is a much more advanced off-chain protocol that enabled bidirectional move-
ment of funds, and also used hashed timelock contracts (HTLCs) to enable
multi-hop payments that are end-to-end secure. The central idea of Light-
ning is to invalidate an old state by punishing the participant publishing
18it, and claiming all the funds in the channel. This however introduces an
intrinsic asymmetry in the information tracked by each participant. The
replaced states turn into toxic information as soon as they are replaced, and
leaking that information may result in funds being stolen. The asymmetry
also limits Lightning to two participants.
Duplex Micropayment Channels [3], a design created in parallel to the
Lightning Network, also offer bidirectional movement of funds. They rely
on decreasing timelocks, arranged in an invalidation tree, to replace earlier
states. The major downsides of this design are the limited number of re-
placements, since the timelocks can only be counted down to the current
time. The invalidation tree extended the range of timelocks, however this
came at the cost of more on-chain transactions in the non-collaborative close
case.
All of the previous protocols had one major issue: since the transactions
need to be signed potentially hours or days before they were released into
the network, the participants would have to estimate the future fees to be
able to ensure a timely confirmation. This is particularly important for the
Lightning Network and Duplex Micropayment Channels, since they rely on
timelocks to allow a defrauded party to react. While the need to guarantee
timely confirmation is also true for eltoo, the need to estimate future fees
was completely removed. In eltoo the fees are added a posteriori at the time
the transaction is published, and, should the fee turn out to be insufficient
it can be amended simply by creating a new version of the transaction with
higher fees a broadcasting it.
The ability to extend the protocol to a larger number of participants
also means that it can be used for other protocols, such as the channel
factories presented by Burchert et al. [2]. Prior to eltoo this used the Duplex
Micropayment Channel construction, which resulted in a far larger number
of transactions being published in the case of a non-cooperative settlement
of the contract.
Finally, it is worth noting that the update mechanism presented in this
paper is a drop-in replacement for the update mechanism used in the Light-
ning Network specification [8]. It can be deployed without invalidating the
ongoing specification efforts by the specification authors or the implementa-
tions currently being deployed. This is possible since the existing stack of
transport, multi-hop and onion routing layers is orthogonal to the update
mechanism used in the update layer.
