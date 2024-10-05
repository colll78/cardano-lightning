---
title: Managing the multisig wallet
---

For managing project funds we use a multisig wallet.
There are some internal helpers for managing this.

## Cutting The Pie

This is a simple tool for creating wallets and mutlisig scripts and txs.
Note, access to a cardano node is required to build and submit txs.

Example flow:

- Setup a working directory, and create an alias to the `cut-the-pie.py` program

```bash
alias ctp="repo/root/bin/cut-the-pie.py"`
```

- `ctp create-wallet` generates a signing key and derives public keys and addresses (mainnet and testnet) from it.
  Create a bunch of participants:

```bash
ctp create-wallet -o wallet-1
ctp create-wallet -o wallet-2
ctp create-wallet -o wallet-3
```

- Inspect the README.md and other files in the generated directories.

```sample
$ ls wallet-1
addr.pay  addr.prv  addr.pub  addr.skey  addr_test.pay  mnemonic  README.md  root.prv
```

- Create a multisig native script:

```sh
ctp create-multi-sig -a $(cat wallet-1/addr.pay) -a $(cat wallet-2/addr.pay) -a $(cat wallet-3/addr.pay) -m 2 -o multi-sig
```

- Inspect the output in the generated directory

```sample
$ ls multi-sig
addr.pay  addr_test.pay  script.json
```

```sh
cat multi-sig/script.json
```

Outputs

```json
{
  "type": "atLeast",
  "required": 2,
  "scripts": [
    {
      "type": "sig",
      "keyHash": "bcb502ce6806837d84704eabf8185d7e2b9b062c4a637f8b01e569ba"
    },
    {
      "type": "sig",
      "keyHash": "98ad386f699d191025586db3b0ea208611203ca3daae8ad53cde4435"
    },
    {
      "type": "sig",
      "keyHash": "3d5cab08137ed75eb32a44da956d274480866405a54c77aa30960ecb"
    }
  ]
}
```

- The generated address is derived from the scripthash for both payment and staking credentials. Note 1 byte header `30` and repeated 28 bytes ending with `8988`:

````sample
$ cat ~/multi-sig/addr_test.pay | bech32
30b6f2452887b3754ff1b3ba72588da03215b5501feac5ecce2dac8988b6f2452887b3754ff1b3ba72588da03215b5501feac5ecce2dac8988
    ```
* This is our testnet address for this particular multisig:

```sample
$ cat ~/multi-sig/addr_test.pay
addr_test1xzm0y3fgs7eh2nl3kwa8ykyd5qeptd2srl4vtmxw9kkgnz9k7fzj3panw48lrva6wfvgmgpjzk64q8l2chkvutdv3xyqfw2auw
````

- As an example let's assume that we have some UTxO which is locked at our multi-sig (2 out of 3) address and which we want to spend:

```bash
cardano-cli query utxo \
  --testnet-magic 1 \
  --address addr_test1xzm0y3fgs7eh2nl3kwa8ykyd5qeptd2srl4vtmxw9kkgnz9k7fzj3panw48lrva6wfvgmgpjzk64q8l2chkvutdv3xyqfw2auw
```

```sample
TxHash                                 TxIx        Amount
--------------------------------------------------------------------------------------
41ec0b4651013f176d641de8327a6956a4c295af9f8d4d85873d0a2f1552f5b1     1        8800000 lovelace + TxOutDatumNone
```

- Construct the tx.

```bash
ctp cut-the-pie \
  --script-file multi-sig/script.json \
  -o "$(cat wallet-1/addr_test.pay)+1000000" \
  -o "$(cat wallet-2/addr_test.pay)+1000000" \
  -o "$(cat wallet-3/addr_test.pay)+1000000" \
  --tx-in '41ec0b4651013f176d641de8327a6956a4c295af9f8d4d85873d0a2f1552f5b1#1' \
  --testnet-magic 1
```

Outputs

```sample
Transaction file 'tx.raw' has been created successfully.
```

- One user/wallet signs and outputs a signed tx.

```bash
cardano-cli transaction sign \
  --tx-file tx.raw \
  --testnet-magic 1 \
  --signing-key-file wallet-1/addr.skey \
  --out-file tx-signed-1.raw
```

Note that one signature is insufficient

```bash
cardano-cli transaction submit --testnet-magic 1 --tx-file tx-signed-1.raw
```

```sample
Command failed: transaction submit  Error: Error while submitting tx: ShelleyTxValidationError ShelleyBasedEraBabbage (ApplyTxError (UtxowFailure (AlonzoInBabbageUtxowPredFailure (ShelleyInAlonzoUtxowPredFailure (ScriptWitnessNotValidatingUTXOW (fromList [ScriptHash "b6f2452887b3754ff1b3ba72588da03215b5501feac5ecce2dac8988"])))) :| []))
```

- The output file is given to a second user/wallet/participant
  who is then able to sign and submit it.

```bash
cardano-cli transaction sign \
  --tx-file tx-signed-1.raw \
  --testnet-magic 1 \
  --signing-key-file wallet-2/addr.skey \
  --out-file tx-signed-2.raw
cardano-cli transaction submit \
  --testnet-magic 1 \
  --tx-file tx-signed-2.raw
```

Which hopefully outputs

```sample
Transaction successfully submitted.
```
