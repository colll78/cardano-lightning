# Cardano Lightning : L2 Peer Protocol Spec

This document covers the basic message structure and base protocol messages (like `init` and `ping-poing`) and peer channel protocol which is responsible for opening, closing, and maintaining a channel between two peers. In other words we loosely follow and cover the scope of the BLN [bolt#1](https://github.com/Lighting/bolts/blob/master/01-messaging.md) and [bolt#2](https://github.com/lightning/bolts/blob/master/02-peer-protocol.md) in this document. There are three phases: establishment, normal operation, and closing.

## Base Protocol

Each peer connection MUST use a single, shared link for all channel messages, with messages distinguished by their channel IDs.

### Connection and the Message Serialization

We assume that the secure communication channel is already established between two peers and that authentication of the partners nodes is done already. The authentication and the transport layer security is out of the scope of this document.

We decided to use [Protocol Buffers](https://protobuf.dev/) for the message serialization so we use protobuf format to describe the messages. Some parts of the protocol rely on CBOR encoded structures (`cheque`, `snapshot` etc.) which are not directly exchanged but are rather reconstructed by both partners so only the signatures are exchanged. These payloads will be specified through separate CDDLs.

### Basic Message Structure

Each message is a protobuf message with the following structure:

```protobuf
message Message {
  uint32 type = 1;
  bytes payload = 2;
}
```

### Messages

```haskell
type Index = Integer

-- Should we introduce "feature flags" similar to BLN:
data Version = Version1

-- 28 bytes of blake2b hash
data CurrencySymbol = ByteString

-- 32 bytes of some hash plus extra payload
data ChannelId = ByteString

type Amount = Integer

type TestnetMagic = Integer

data NetworkId = Mainnet | Testnet TestnetMagic

type Milliseconds = Integer

type POSIX = Integer

-- TODO: This will be replaced by rather closed and long enum
--       with some extra payload
type RejectionReason = String

type TxOutRef = (ByteString, Integer)

-- 32 bytes of sha256 hash
type Sha256Hash = ByteString

type Ed25519PubKey = ByteString

-- 64 bytes of Ed25519 signature
type Signature = ByteString

data Snapshot = Snapshot
    { amount0 :: Amount
    , amount1 :: Amount
    , idx0 :: Index
    , idx1 :: Index
    , exc0 :: [Integer]
    , exc1 :: [Integer]
    }

-- TODO:
-- Should we notify separately about tx settlement attempt and about
-- the step finalization like `FundsAdd` and `FundsAdded/FundsAddConfirmed`?
-- In BLN splicing proposal there is no separate message but it is probablyand
-- assumed from the context (the transcation creation precedes the tx settlement).
-- * If we won't notify the partner about tx settlement attempt then we can have collisions
-- but maybe that is not a problem - we have to monitor the chain anyway and discover changes.
-- * If we notify separately about the attempt and provide the details then we have to introduce
-- probably some kind of abort action if it was colliding etc.

-- Tx verification through Mithril:
-- * We have to be prepared that in order to use Mithril efficiently (using its current API) we will
-- use `/proof/cardano-transaction`'
-- * In order to use that endpoint we have to actually construct transaction client side
-- * In order to construct transaction on the client side we should:
--      * Receive or reconstruct the transaction CBOR
--      * Check the UTxO of that transaction
-- * Mithril will have probably in the future queries like "utxo-by-addresses" - it seems that they are not 
-- part of the aggregator HTTP API yet. It seem rather useless in our case anyway.
type Tx = ByteString

-- During any negociation we use ranges to speed up the process
data Message
    = Init Version
    | Ping
    | Pong
    | Reject
        { channelId :: ChannelId
        , reasons :: [RejectionReason]
        }
    | Open
        { netorkId :: NetworkId
        , channelId :: ChannelId
        , currencySymbol :: CurrencySymbol
        , fundingAmount :: [Amount, Amount]
        , giftAmount :: Amount
        , respondPeriod :: [Milliseconds, Milliseconds]
        , minimumDepth :: [Integer, Integer]
        , minHtlcValue :: [Amount, Amount]
        , maxHtlcValue :: [Amount, Amount]
        , maxTotalHtlcValue :: [Amount, Amount]
        , maxHtlcCount :: [Integer, Integer]
        , pubKey :: Ed25519PubKey
        }
    | Accept
        { channelId :: ChannelId
        , fundingAmount :: Amount
        , respondPeriod :: Milliseconds
        , minimumDepth :: Integer
        , minHtlcValue :: Amount
        , maxHtlcValue :: Amount
        , maxTotalHtlcValue :: Amount
        , maxHtlcCount :: Integer
        , pubKey :: Ed25519PubKey
        }
    | ChannelStaged
        { channelId :: ChannelId
        , txOutRef :: TxOutRef
        -- Mithril support? Should it be added across
        -- , tx :: Tx
        }
    | FundsAdded
        { channelId :: ChannelId
        , blockNumber :: Integer
        -- ^ Worth including as we can clearly detect
        -- rollback on the other side?
        , txOutRef :: TxOutRef
        , amount :: Amount
        }
    | AddHtlc
        { channelId :: ChannelId
        , htlcIdx :: Integer
        , amount :: Amount
        , timeout :: POSIXMilliseconds
        , lock :: Sha256Hash
        }
    | FulfillHtlc
        { channelId :: ChannelId
        , htlcIdx :: Integer
        , secret :: ByteString
        , signature :: Signature
        }
    -- BLN uses "fail" - `update_fail_htlc` with "reason"
    | HtlcTimeout
        { channelId :: ChannelId
        , htlcIdx :: Integer
        }
    -- Let's chat about it - it is described in the basic
    -- set of the responses.
    -- | HtlcCancel
    --     { channelId :: ChannelId
    --     , htlcIdx :: Integer
    --     }
    | AddCheque
        { channelId :: ChannelId
        , chequeIdx :: Index
        , amount :: Amount
        , signature :: Signature
        }
    -- Should we exchange those (so pass the same `Shapshot` back) or
    -- should we introduce separate response which
    -- have compressed version of the snapshot like `(amount0, amount1)`?
    | SignedSnapshot
        { channelId :: ChannelId
        , snapshot :: Snapshot
        , signature :: Ed25519Signature
        }
    -- Should we include a full redeemer info or tx or none?
    | ChannelClosed
        { channelId :: ChannelId
        , txOutRef :: TxOutRef
        }
    | ChannelResponded
        { channelId :: ChannelId
        , txOutRef :: TxOutRef
        }
    | ChannelElapsed
        { channelId :: ChannelId
        , txOutRef :: TxOutRef
        }
    | ChannelRecovered
        { channelId :: ChannelId
        , txOutRef :: TxOutRef
        }
    | LocksFreed
        { channelId :: ChannelId
        , secrets :: [(Index, Maybe ByteString)]
        , txOutRef :: TxOutRef
        }
    | ChannelUnstaged
        { channelId :: ChannelId
        }
```


### Setup and Control

#### `init`
Copypasta bolt#1

#### `ping` and `pong`
Copypasta bold#2

## Channel Establishment

### `ChannelAdd

## Channel Operation

## Channel Closure

### Protobuf Spec

```protobuf
syntax = "proto3";

package cardano_lightning;

// Version enumeration
enum Version {
  VERSION1 = 0;
}

// NetworkId message
message NetworkId {
  oneof network {
    Mainnet mainnet = 1;
    Testnet testnet = 2;
  }
}

message Mainnet {
  // No fields needed for Mainnet
}

message Testnet {
  int64 testnetMagic = 1;
}

// TxOutRef message
message TxOutRef {
  bytes txHash = 1;
  int64 index = 2;
}

// Snapshot message
message Snapshot {
  int64 amount0 = 1;
  int64 amount1 = 2;
  int64 idx0 = 3;
  int64 idx1 = 4;
  repeated int64 exc0 = 5;
  repeated int64 exc1 = 6;
}

// Range message for integer ranges
message RangeInt64 {
  int64 min = 1;
  int64 max = 2;
}

// Message definitions
message Message {
  oneof content {
    Init init = 1;
    Ping ping = 2;
    Pong pong = 3;
    Reject reject = 4;
    Open open = 5;
    Accept accept = 6;
    FundsAdded funds_added = 7;
    AddHTLC add_htlc = 8;
    FulfillHTLC fulfill_htlc = 9;
    AddCheque add_cheque = 10;
    SignedSnapshot signed_snapshot = 11;
    ChannelClosed channel_closed = 12;
  }
}

message Init {
  Version version = 1;
}

message Ping {
  // Empty message
}

message Pong {
  // Empty message
}

message Reject {
  bytes channelId = 1;
  repeated string reasons = 2;
}

message Open {
  NetworkId networkId = 1;
  bytes channelId = 2;
  bytes currencySymbol = 3;
  RangeInt64 fundingAmount = 4;
  int64 giftAmount = 5;
  RangeInt64 respondPeriod = 6;
  RangeInt64 minimumDepth = 7;
  RangeInt64 minHTLCValue = 8;
  RangeInt64 maxHTLCValue = 9;
  RangeInt64 maxTotalHTLCValue = 10;
  RangeInt64 maxHTLCCount = 11;
  bytes pubKey = 12;
}

message Accept {
  bytes channelId = 1;
  int64 fundingAmount = 2;
  int64 respondPeriod = 3;
  int64 minimumDepth = 4;
  int64 minHTLCValue = 5;
  int64 maxHTLCValue = 6;
  int64 maxTotalHTLCValue = 7;
  int64 maxHTLCCount = 8;
  bytes pubKey = 9;
}

message FundsAdded {
  bytes channelId = 1;
  int64 blockNumber = 2;
  TxOutRef txOutRef = 3;
  int64 amount = 4;
}

message AddHTLC {
  bytes channelId = 1;
  int64 htlcIx = 2;
  int64 amount = 3;
  int64 timeout = 4; // POSIX time in milliseconds
  bytes lock = 5;    // Sha256Hash
}

message FulfillHTLC {
  bytes channelId = 1;
  int64 htlcIx = 2;
  bytes preimage = 3;
  bytes signature = 4;
}

message AddCheque {
  bytes channelId = 1;
  int64 chequeIx = 2;
  int64 amount = 3;
  bytes signature = 4;
}

message SignedSnapshot {
  bytes channelId = 1;
  Snapshot snapshot = 2;
  bytes signature = 3;
}

message ChannelClosed {
  bytes channelId = 1;
  string reason = 2;
}
```
