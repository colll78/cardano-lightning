# #0 : Introduction and Index

These documents outline a layer-2 protocol for the off-chain transfer of Cardano Fungible Tokens through mutual cooperation between participants. While the protocol primarily operates off-chain, it relies on on-chain transactions for enforcement when necessary.

Some aspects of the protocol are nuanced, and we have made an effort to clarify the motivations and reasoning behind our decisions. However, we acknowledge that there may still be areas that are unclear or in need of improvement. If you encounter any confusing or incorrect information, please don't hesitate to contact us and provide feedback.

1. [#1]() : Channels & L1 concerns


## A Short Introduction to Lightning

**Cardano Lightning** is a protocol designed for facilitating fast payments with *Cardano Fungible Tokens* by utilizing a network of channels. This protocol draws significant inspiration from the [Bitcoin Lightning Network Specification](https://github.com/lightning/bolts/blob/master/README.md), while uniquely leveraging the [Extended UTXO Model](https://iohk.io/en/research/library/papers/the-extended-utxo-model/) and the advanced scripting capabilities of the Cardano blockchain.

### Mono-asset Channels

Lightning works by establishing *monoasset channels*: 
2 participants create a Lightning payment channel that contains some amount of a Fungible Token (e.g. *5 ₳ , 500 DJED, 400 USDC*) that they've locked up on the Cardano network. 

## Digital Cheque


Difference with BLN 

- Account DigitalCheque
- Mono Asset vs Multi Asset Ledger
- Cheque concept vs raw Tx management
- Script capabilities vs mutlisig 2-2 and
    - Level of logic : 
        - Tx for Bitcoin vs Redeemer for Cardano

- Onchain State machine Logic :
   -
   - add 
   - sub 
   - Fungible Token vs Coin of the ledger