> 5
> Analysis
> The eltoo renegotation protocol simplifies existing off-chain protocols, and
> enables new use-cases for off-chain protocols. In the following we will analyze
> the security assumptions as well as lay out some of the new enabled use-cases.
> 155.1
> Safety
> We define a state i, consisting of the tuple of update transaction Tu,i and
> settlement transaction Su,i , to be committed if the settlement transaction is
> confirmed in the blockchain. For simplification we consider any transaction
> to be confirmed if it appears in a block, i.e., we do not consider blockchain
> reorganizations.
> We define an unsafe execution of the protocol as any execution in which
> a participant in the off-chain protocol, making use of the eltoo renegotiation
> protocol, is able to commit an old state to the blockchain. Consequently any
> execution in which only the final state is eventually committed is considered
> safe. This matches the above definition of confirmation since any confirma-
> tion of a settlement transaction that is not the final settlement is considered
> sufficient to fail the protocol, even in the presence of reorganizations.
> Notice that the setup of the contract is considered safe. It is easy to
> see that, if the first update transaction and settlement transaction is signed
> before the setup transaction is signed, then funds never are locked in without
> the ability to settle again.
> We consider the scenario with two participants in the protocol, one of
> which is an attacker and the other one, the victim, behaves correctly. It is
> the goal of the attacker to commit an old state, that maximized its payout.
> For this purpose the attacker may store an arbitrary number of intermediate
> update transactions, while the victim only stores the latest set of update and
> settlement transactions.
> At any point in time the attacker may broadcast an old update transac-
> tion Tu,i , in the hope of also confirming Ts,i . Ts,i however will have to wait
> for the OP_CSV timeout in the update’s output script to expire. This gives
> the victim the opportunity of broadcasting the final update transaction as a
> reaction. The victim can either witness Tu,i being broadcast or by seeing it
> confirmed in the blockchain. The reaction consists of creating two versions
> of the latest Tu,j transaction with j > i:
> 0 bound to the setup output, effectively doublespending T ;
> • Tu,j
> u,i
> 00 bound to the output of T , which doublespends T ;
> • Tu,j
> u,i
> s,i
> Generally speaking, no matter which update transaction the attacker
> broadcasts, the victim can doublespend both the update transaction itself,
> or, in the case the update transaction succeeds, it can doublespend the settle-
> ment. The eventual success of the doublespend is guaranteed by the OP_CSV
> 16timeout, which ensures that the doublespend is prioritized over the attacker’s
> settlement transaction.
> The safety of the protocol therefore depends on two key assumptions:
> • The victim can detect an attack in time to react to it, either by actively
> participating in the network, or by outsourcing the reaction to a third
> party;
> • The later update transaction can be confirmed in the specified time to
> doublespend the outdated update;
> Both of these depend on the OP_CSV timeout duration, so if a user is
> offline for a prolonged period it may chose a higher timeout. Higher timeouts
> however also mean longer waiting time to retrieve its own funds in case the
> other participant stops cooperating. The timeout can be collaboratively
> chosen by the participants in order to optimize the safety and liveness of the
> protocol, depending on the specific capabilities of the participants.
> Notice that the settlement phase is little more than an update without
> the need for a timeout, and therefore the same safety analysis applies.
> 5.2
> Extending the protocol to more parties
> As mentioned above the storage requirements for participants consist of the
> latest tuple of update and settlement transaction. This is because they can
> be rebound to any of the intermediate update transactions in case it gets
> broadcast. This is in stark contract to the Lightning Network, where the
> reaction to a previous state being published needs to tailored to that specific
> state.
> In Lightning the information stored is asymmetric, i.e., the information
> stored by one endpoint is different from the information stored by the other.
> In fact the security of Lightning hinges on the information being kept private
> since publishing it could result in the funds being claimed by the other
> endpoint. We refer to this information about previous states as being toxic.
> With eltoo the information stored by the participants is symmetric, elimi-
> nating the toxic information, and greatly simplifying the protocol as a whole.
> The information being symmetric also enables extending the protocol to any
> number of participants, since there is no longer a combinatorial problem of
> how to react to a specific participant misbehaving.
> The protocol can be generalized to any number of participants by simply
> gathering all the settlement and update public keys of the participants and
> listing them in the public key list. Due to the size constraints imposed on
> 17the output scripts it is currently not possible to go beyond 7 participants.
> This results from each participant contributing 2 public keys, 33 bytes each,
> and the script size for P2SH scripts being limited to 520 bytes.
> This limit is raised to 10’000 bytes for P2WSH scripts, allowing up to
> 150 participants, but producing very costly on-chain transactions. However,
> with the introduction of schnorr signatures, and aggregatable signature it is
> possible to extend this to any number of participants, and without incurring
> the on-chain cost, since all public keys and signatures are aggregated into a
> single public key and a single signature.

