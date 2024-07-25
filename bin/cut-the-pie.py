#!/usr/bin/env python3

import json
import os
import subprocess
import argparse
import stat
import textwrap

def run_command(command):
    return subprocess.run(command, shell=True, check=True, capture_output=True, text=True).stdout.strip()

def create_wallet(output_dir):
    # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    os.chmod(output_dir, stat.S_IRWXU)
    os.chdir(output_dir)

    mnemonic = run_command('cardano-address recovery-phrase generate --size 15')
    with open('mnemonic', 'w') as f:
        f.write(mnemonic)
    # bytes of "extended" root private key
    run_command(f'echo "{mnemonic}" | cardano-address key from-recovery-phrase Shelley > root.prv')
    # bytes of the first derivate private key
    run_command('cat root.prv | cardano-address key child 1852H/1815H/0H/0/0 > addr.prv')
    # Unhashed pubkey bytes without the byte header: network prefix etc.
    run_command('cat addr.prv | cardano-address key public --without-chain-code > addr.pub')

    # Redundant but  useful for futher cardano-cli interaction like singing
    run_command('cardano-cli key convert-cardano-address-key --shelley-payment-key --signing-key-file addr.prv --out-file addr.skey');
    run_command('cardano-cli key verification-key --signing-key-file addr.skey --verification-key-file addr.vkey');

    # blake2b224 hashed with mainnet header
    bech32_address = run_command('cat addr.pub | cardano-address address payment --network-tag 1')
    with open('addr.pay', 'w') as f:
        f.write(bech32_address)

    # blake2b224 hashed with testnet header
    bech32_address_test = run_command('cat addr.pub | cardano-address address payment --network-tag 0')
    with open('addr_test.pay', 'w') as f:
        f.write(bech32_address_test)

    README = textwrap.dedent(f"""\
    ## Wallet info

    * `mnemonic`: 15-word mnemonic phrase
    * `root.prv`: Extended root private key
    * `addr.prv`: Private key derived using `1852H/1815H/0H/0/0`
    * `addr.pub`: Corresponing public key unhashed
    * `addr.pay`: Bech32 address (blake2b224 hashed) with proper header for mainnet
        Meaning: `cat wallet/addr.pub | bech32 | xxd -r -p -c0 | b2sum -l 224` == byte header + `cat wallet/addr.pay | bech32`
    * `addr_test.pay`: Bech32 address (blake2b224 hashed) with proper header for testnet
    * `addr.skey`: Signing key - shelley/cardano-cli format
    * `addr.vkey`: Verification key - shelley/cardano-cli format
    """)
    with open('README.md', 'w') as f:
        f.write(README)

    # Set file permissions to 600 (rw-------)
    for file in ['mnemonic', 'root.prv', 'addr.prv', 'addr.pub', 'addr.pay', 'addr_test.pay']:
        os.chmod(file, stat.S_IRUSR | stat.S_IWUSR)

def decode_bech32(address):
    try:
        return run_command(f'echo {address} | bech32').strip()
    except subprocess.CalledProcessError:
        raise ValueError(f"Invalid bech32 address: {address}")

def get_script_addresses(script_file):
    # Compute policy ID
    policy_id = run_command(f'cardano-cli transaction policyid --script-file {script_file}')

    # Define header bytes
    mainnet_header = "31"
    testnet_header = "30"

    # Combine bytes
    mainnet_bytes = mainnet_header + policy_id + policy_id
    testnet_bytes = testnet_header + policy_id + policy_id

    # Generate Bech32 addresses
    mainnet_address = run_command(f'echo {mainnet_bytes} | bech32 addr')
    testnet_address = run_command(f'echo {testnet_bytes} | bech32 addr_test')

    return (mainnet_address, testnet_address)

def create_multi_sig(majority, signers, output_dir):
    if len(signers) < 2:
        raise ValueError("At least two signers are required")

    if majority > len(signers):
        raise ValueError("Majority cannot be greater than the number of signers")

    os.makedirs(output_dir, exist_ok=True)
    os.chdir(output_dir)

    policy = {
        "type": "atLeast",
        "required": majority,
        "scripts": []
    }

    for address in signers:
        decoded = decode_bech32(address)
        key_hash = decoded[2:58]  # Extract bytes 2-29 (28 bytes) in hex
        policy["scripts"].append({
            "type": "sig",
            "keyHash": key_hash
        })

    script_file = 'script.json'
    # Write policy to script.json
    with open(script_file, 'w') as f:
        json.dump(policy, f, indent=4)

    (mainnet_address, testnet_address) = get_script_addresses(script_file)
    # Save addresses to files
    with open('addr.pay', 'w') as f:
        f.write(mainnet_address)
    with open('addr_test.pay', 'w') as f:
        f.write(testnet_address)

    return json.dumps(policy, indent=4)

def cut_the_pie(script_file, tx_in, outputs, testnet_magic=None):
    # Validate outputs
    validated_outputs = []
    total_output_amount = 0
    for output in outputs:
        (address, amount) = output.split('+')
        if not (address.startswith('addr1') or address.startswith('addr_test1')):
            raise ValueError(f"Invalid address format: {address}")
        try:
            decode_bech32(address)
        except ValueError as e:
            raise ValueError(f"Invalid address: {address}. Error: {str(e)}")
        try:
            amount = int(amount)
            total_output_amount += amount
        except ValueError:
            raise ValueError(f"Invalid amount: {amount}")
        validated_outputs.append((address, amount))

    # Compute policy address
    (mainnet_address, testnet_address) = get_script_addresses(script_file)
    policy_address = testnet_address if testnet_magic else mainnet_address

    # TODO: This could be optionally provided together with TxOutRef so we
    # don't have to query the blockchain for the UTxO.
    query_cmd = ["cardano-cli", "query", "utxo", "--tx-in", tx_in, "--output-json"]
    if testnet_magic:
        query_cmd.extend(["--testnet-magic", str(testnet_magic)])
    else:
        query_cmd.append("--mainnet")

    utxo_json = json.loads(run_command(" ".join(query_cmd)))
    utxo_value = utxo_json[tx_in]["value"]

    # Calculate total input amount
    total_input_amount = utxo_value["lovelace"]

    # Calculate change amount
    fee = 200000  # Default fee
    change_amount = total_input_amount - total_output_amount - fee

    if change_amount < 0:
        raise ValueError(f"Not enough funds. Input: {total_input_amount}, Output: {total_output_amount}, Fee: {fee}")

    # Construct cardano-cli command
    cmd = [
        "cardano-cli", "transaction", "build-raw",
        "--tx-in", tx_in,
        "--tx-in-script-file", script_file,
        "--fee", str(fee),
    ]

    for (address, amount) in validated_outputs:
        cmd.extend(["--tx-out", f"{address}+{amount}"])

    # Add change output
    cmd.extend(["--tx-out", f"{policy_address}+{change_amount}"])

    # if testnet_magic:
    #     cmd.extend(["--testnet-magic", str(testnet_magic)])
    # else:
    #     cmd.extend(["--mainnet"])

    cmd.extend(["--out-file", "tx.raw"])

    # Execute the command
    try:
        subprocess.run(cmd, check=True)
        print("Transaction file 'tx.raw' has been created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating transaction: {e}")

def main():
    parser = argparse.ArgumentParser(description="Cardano wallet and multi-sig script generation tool")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Create wallet subparser
    create_wallet_parser = subparsers.add_parser('create-wallet', help="Create a new wallet")
    create_wallet_parser.add_argument('--output-dir', '-o', required=True, help="Directory to store wallet files")

    # Create multi-sig subparser
    create_multi_sig_parser = subparsers.add_parser('create-multi-sig', help="Create a multi-sig spending validator")
    create_multi_sig_parser.add_argument('--majority', '-m', type=int, required=True, help="Number of required signatures")
    create_multi_sig_parser.add_argument('--signer-address', '-a', action='append', required=True, help="Signer address (can be repeated)")
    create_multi_sig_parser.add_argument('--output-dir', '-o', required=True, help="Directory to store output files")

    cut_the_pie_parser = subparsers.add_parser('cut-the-pie', help="Create a transaction to distribute funds")
    cut_the_pie_parser.add_argument('--script-file', required=True, help="Path to the script file")
    cut_the_pie_parser.add_argument('--tx-in', required=True, help="Input UTxO")
    cut_the_pie_parser.add_argument('--output', '-o', action='append', required=True, help="Output in format 'address+amount'")
    cut_the_pie_parser.add_argument('--testnet-magic', type=int, help="Network magic for testnet")

    args = parser.parse_args()

    if args.command == 'create-wallet':
        create_wallet(args.output_dir)
    elif args.command == 'create-multi-sig':
        try:
            spending_validator = create_multi_sig(args.majority, args.signer_address, args.output_dir)
        except ValueError as e:
            print(f"Error: {str(e)}")
    elif args.command == 'cut-the-pie':
        cut_the_pie(args.script_file, args.tx_in, args.output, args.testnet_magic)

if __name__ == "__main__":
    main()


