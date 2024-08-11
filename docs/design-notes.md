# Cardano Lightning : Design notes

This is a working document hosting our current ideas about the protocols design and features.

## Ideas to be unpacked

- multi cheque channels 
- Proof of life payments 
- minimum deposit
- dynamic fees

## Components

+ pwa for L2 payments 
+ pwa for L1/L2 account management 

## Design

### L1

#### State

+ What state do participants track? 

```ts
type State = {
    latestCheque : BigInt,
    balance: BigInt,
    excludedCheques: BigInt[]
}
```

#### Constants 

The time each participant has to resolve their commitments on the L1
in the case that something goes wrong.
```ts
const L1_RESOLUTION_PERIOD = P = 24 * 60 * 60 * 1000 // Day 
```

#### Datatypes

A cheque commitment comes with a signed payload.
```ts
type Payload = {
  validUntil : Timestamp,
  hashedSecret: ByteArray,
}
```
These can be resolved on the L1 if there is failure to agree on the L2.
The secret must be provided. 

### L2 

TODO

## Examples 

### One payment, One hop

#### Two parties

##### Without payment confirmation

```mermaid
 sequenceDiagram
  participant Consumer
  participant Provider

  Consumer-->> Provider: Thx. Sending 10.2$
  Consumer->> Provider: Here's the 10.2$ cheque

  Consumer-->> Provider: Thx. Sending another 5$ 
  Consumer->> Provider: Here's the 15.2$ cheque
```

##### With payment confirmation

```mermaid
 sequenceDiagram
  participant Consumer
  participant Provider

  Consumer-->> Provider: Thx. Sending funds
  Provider-->> Consumer: Cool. Here's a <hashed-secret>. I know  Gateway
  Consumer->>Provider: Here's 10$ cheque commitment with <hashed-secret>
  Provider->> Consumer: Thx. Here's the secret
  Consumer->> Provider: Here's the 10.2$ cheque
```

#### Well behaved

```mermaid
 sequenceDiagram
  participant Consumer
  participant Gateway
  participant Provider

  Consumer-->> Provider: Thx. Sending funds
  Provider-->> Consumer: Cool. Here's a <hashed-secret>. I know  Gateway
  Consumer->> Gateway: Here's a 10.2$ cheque commitment
  Note over  Consumer, Gateway: Payload( 2 * P, <hashed-secret> )
  Gateway->>Provider: Here's 10$ cheque commitment with <hashed-secret>
  Note over  Gateway,Provider: Payload( P, <hashed-secret> )
  Provider->> Gateway: Thx. Here's the secret
  Gateway->>Provider: Here's the 10$ cheque
  Gateway->> Consumer: Here's the secret
  Consumer->> Gateway: Here's the 10.2$ cheque
```

#### Evil middleman 

+ How does "Consumer" know "Gateway" is paying Provider the full fee?! 

Provider will only reveal the secret if it matches their expectations. 
Otherwise no money will change hands. 


#### Evil Recipient

As before but Provider doesn't play nice.
He reveals the the secret only on the L1.

```mermaid
 sequenceDiagram
  participant Consumer
  participant Gateway
  participant Provider

  Consumer-->>Provider: Thx. Sending funds
  Provider-->>Consumer: Cool. Here's a <hashed-secret>. I know Gateway
  Consumer->>Gateway: Here's a 10.2$ cheque commitment
  Note over Consumer,Gateway: Payload( 2 * P, <hashed-secret> )
  Gateway->>Provider: Here's 10$ cheque commitment with <hashed-secret>
  Note over Gateway,Provider: Payload( P, <hashed-secret> )
  Provider-->Gateway: **SILENCE**
  Provider->>L1: Cash cheque commitment with secret
  Gateway->L1: Gateway sees Provider's secret
  Gateway->>Consumer: Here's the secret
  Consumer->>Gateway: Here's the 10.2$ cheque
```

#### No resolution at route source

```mermaid
 sequenceDiagram
  participant Consumer
  participant Gateway
  participant Provider

  Consumer-->>Provider: Thx. Sending funds
  Provider-->>Consumer: Cool. Here's a <hashed-secret>. I know Gateway
  Consumer->>Gateway: Here's a 10.2$ cheque commitment
  Note over Consumer,Gateway: Payload( 2 * P, <hashed-secret> )
  Gateway->>Provider: Here's 10$ cheque commitment with <hashed-secret>
  Note over Gateway,Provider: Payload( P, <hashed-secret> )
  Provider->>Gateway: Thx. Here's the secret
  Gateway->>Provider: Here's the 10$ cheque
  Gateway->>Consumer: Here's the secret
  Consumer->>Gateway: ** SILENCE **
  Gateway->>L1: Cash cheque commitment with secret
```
Gateway deems Consumer unreliable and my close the account. 

#### No resolution on route

```mermaid
 sequenceDiagram
  participant Consumer
  participant Gateway
  participant Provider

  Consumer-->>Provider: Thx. Sending funds
  Provider-->>Consumer: Cool. Here's a <hashed-secret>. I know Gateway
  Consumer->>Gateway: Here's a 10.2$ cheque commitment
  Note over Consumer,Gateway: Payload( 2 * P, <hashed-secret> )
  Gateway->>Provider: Here's 10$ cheque commitment with <hashed-secret>
  Note over Gateway,Provider: Payload( P, <hashed-secret> )
  Provider->>Gateway: Thx. Here's the secret
  Gateway-->Provider: ** SILENCE **
  Provider->>L1: Cash cheque commitment with secret
  Gateway->L1: Gateway sees Provider's secret
  Gateway->>Consumer: Here's the secret
  Consumer->>Gateway: Here's the 10.2$ cheque
```
Provider deems Gateway unreliable and closes the account.

### Multi-cheque 

We use Channels to handle mutliple unresolved cheques simultaneously.
This prevents channels being blocked during resolution.
Consider the case that: 

1. Consumer pays Provider via Gateway and then Dennis before resolving the first cheque.
2. And the cheque to Provider resolves before or after Dennis. 
3. Or the cheque to Provider fails to resolve.  

TODO
