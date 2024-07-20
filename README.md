# cardano-lightning

## Overview

Currently we use monorepo approach for creating the preliminary specification and POC implementation. Later on we will split this into separate repositories.

## Administration

Some internal helpers for managing our project etc.

### Cutting The Pie

Simple tool for creating wallets and mutlisig scripts and txs. Unfortunatelly for the tx build up and submission we need cardano node for a given network. Example flow:

  *  Creating a bunch of participants:

      ```bash
      $ ./bin/cut-the-pie.py create-wallet -o wallet-1
      $ ./bin/cut-the-pie.py create-wallet -o wallet-2
      $ ./bin/cut-the-pie.py create-wallet -o wallet-3
      ```

  * We have more than enough information stored in output directories (wallet-X/README.md explains the details):

      ```bash
      $ ls wallet-1
      addr.pay  addr.prv  addr.pub  addr.skey  addr_test.pay  mnemonic  README.md  root.prv
      ```
  * Now we can create a multisig native script:
      ```
      $ ./bin/cut-the-pie.py create-multi-sig -a $(cat wallet-1/addr.pay) -a $(cat wallet-2/addr.pay) -a $(cat wallet-3/addr.pay) -m 2 -o multi-sig
      ```
  * Again all the required info is in the output directory:
      ```
      $ ls multi-sig
      addr.pay  addr_test.pay  script.json
      ```
  * Generate address locks both the stake and assets at the same multisig address (pleaes note 1 byte header `30` and repeated 28 bytes ending with `8988`):
      ```
      $ cat ~/multi-sig/addr_test.pay | bech32
      30b6f2452887b3754ff1b3ba72588da03215b5501feac5ecce2dac8988b6f2452887b3754ff1b3ba72588da03215b5501feac5ecce2dac8988
      ```
  * So this is our testnet address for this particular multisig:
      ```
      $ cat ~/multi-sig/addr_test.pay
      addr_test1xzm0y3fgs7eh2nl3kwa8ykyd5qeptd2srl4vtmxw9kkgnz9k7fzj3panw48lrva6wfvgmgpjzk64q8l2chkvutdv3xyqfw2auw

      ```

  * Let's assume that we have some UTxO which we want to spend:

      ```
      $ cardano-cli query utxo  --testnet-magic 1 --address addr_test1xzm0y3fgs7eh2nl3kwa8ykyd5qeptd2srl4vtmxw9kkgnz9k7fzj3panw48lrva6wfvgmgpjzk64q8l2chkvutdv3xyqfw2auw
                                  TxHash                                 TxIx        Amount
      --------------------------------------------------------------------------------------
      41ec0b4651013f176d641de8327a6956a4c295af9f8d4d85873d0a2f1552f5b1     1        8800000 lovelace + TxOutDatumNone
      ```
  * We can create multi-sig transaction given the UTxO and outputs which we want to have:

      ```
      $ ./bin/cut-the-pie.py cut-the-pie --script-file multi-sig/script.json -o "$(cat wallet-1/addr_test.pay)+1000000" -o "$(cat wallet-2/addr_test.pay)+1000000" -o "$(cat wallet-3/addr_test.pay)+1000000" --tx-in '41ec0b4651013f176d641de8327a6956a4c295af9f8d4d85873d0a2f1552f5b1#1' --testnet-magic 1

      Transaction file 'tx.raw' has been created successfully.
      ```
  * Now we can sign it once which is not enough for submission:

      ```
      $ cardano-cli transaction sign --tx-file tx.raw --testnet-magic 1 --signing-key-file wallet-1/addr.skey  --out-file tx-signed-1.raw
      $ cardano-cli transaction submit --testnet-magic 1 --tx-file tx-signed-1.raw
      Command failed: transaction submit  Error: Error while submitting tx: ShelleyTxValidationError ShelleyBasedEraBabbage (ApplyTxError (UtxowFailure (AlonzoInBabbageUtxowPredFailure (ShelleyInAlonzoUtxowPredFailure (ScriptWitnessNotValidatingUTXOW (fromList [ScriptHash "b6f2452887b3754ff1b3ba72588da03215b5501feac5ecce2dac8988"])))) :| []))
      ```
  * We can sign it once again and the submit suceeds:

      ```
      $ cardano-cli transaction sign --tx-file tx-signed-1.raw --testnet-magic 1 --signing-key-file wallet-2/addr.skey  --out-file tx-signed-2.raw
      $ cardano-cli transaction submit --testnet-magic 1 --tx-file tx-signed-2.raw
      Transaction successfully submitted.
      ```
  * Submission is successful because we our required number of signatures is two:

      ```$ cat multi-sig/script.json```
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



