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
    latest_cheque : BigInt,
    balance: BigInt, 
    excluded_cheques: BigInt[]
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
  valid_until : Timestamp,
  hashed_secret: ByteArray,
}
```
These can be resolved on the L1 if there is failure to agree on the L2.
The secret must be provided. 

### L2 

TODO

## Examples 

### One payment, One hop

#### Well behaved

```mermaid
 sequenceDiagram
  participant Service Consumer
  participant Service Provider
  participant Payment Gateway

  Service Consumer-->>Payment Gateway: Thx. Sending funds
  Payment Gateway-->>Service Consumer: Cool. Here's a <hashed-secret>. I know Service Provider
  Service Consumer->>Service Provider: Here's a 10.2$ cheque commitment
  Note over Service Consumer,Service Provider: Payload( 2 * P, <hashed-secret> )
  Service Provider->>Payment Gateway: Here's 10$ cheque commitment with <hashed-secret>
  Note over Service Provider,Payment Gateway: Payload( P, <hashed-secret> )
  Payment Gateway->>Service Provider: Thx. Here's the secret
  Service Provider->>Payment Gateway: Here's the 10$ cheque
  Service Provider->>Service Consumer: Here's the secret
  Service Consumer->>Service Provider: Here's the 10.2$ cheque
```

#### Evil middleman 

+ How does "Service Consumer" know "Service Provider" is paying Payment Gateway the full fee?! 

Payment Gateway will only reveal the secret if it matches their expectations. 
Otherwise no money will change hands. 


#### Evil Recipient

As before but Payment Gateway doesn't play nice.
He reveals the the secret only on the L1.

```mermaid
 sequenceDiagram
  participant Service Consumer
  participant Service Provider
  participant Payment Gateway

  Service Consumer-->>Payment Gateway: Thx. Sending funds
  Payment Gateway-->>Service Consumer: Cool. Here's a <hashed-secret>. I know Service Provider
  Service Consumer->>Service Provider: Here's a 10.2$ cheque commitment
  Note over Service Consumer,Service Provider: Payload( 2 * P, <hashed-secret> )
  Service Provider->>Payment Gateway: Here's 10$ cheque commitment with <hashed-secret>
  Note over Service Provider,Payment Gateway: Payload( P, <hashed-secret> )
  Payment Gateway-->Service Provider: **SILENCE**
  Payment Gateway->>L1: Cash cheque commitment with secret
  Service Provider->L1: Service Provider sees Payment Gateway's secret
  Service Provider->>Service Consumer: Here's the secret
  Service Consumer->>Service Provider: Here's the 10.2$ cheque
```

#### No resolution at route source

```mermaid
 sequenceDiagram
  participant Service Consumer
  participant Service Provider
  participant Payment Gateway

  Service Consumer-->>Payment Gateway: Thx. Sending funds
  Payment Gateway-->>Service Consumer: Cool. Here's a <hashed-secret>. I know Service Provider
  Service Consumer->>Service Provider: Here's a 10.2$ cheque commitment
  Note over Service Consumer,Service Provider: Payload( 2 * P, <hashed-secret> )
  Service Provider->>Payment Gateway: Here's 10$ cheque commitment with <hashed-secret>
  Note over Service Provider,Payment Gateway: Payload( P, <hashed-secret> )
  Payment Gateway->>Service Provider: Thx. Here's the secret
  Service Provider->>Payment Gateway: Here's the 10$ cheque
  Service Provider->>Service Consumer: Here's the secret
  Service Consumer->>Service Provider: ** SILENCE **
  Service Provider->>L1: Cash cheque commitment with secret
```
Service Provider deems Service Consumer unreliable and my close the account. 

#### No resolution on route

```mermaid
 sequenceDiagram
  participant Service Consumer
  participant Service Provider
  participant Payment Gateway

  Service Consumer-->>Payment Gateway: Thx. Sending funds
  Payment Gateway-->>Service Consumer: Cool. Here's a <hashed-secret>. I know Service Provider
  Service Consumer->>Service Provider: Here's a 10.2$ cheque commitment
  Note over Service Consumer,Service Provider: Payload( 2 * P, <hashed-secret> )
  Service Provider->>Payment Gateway: Here's 10$ cheque commitment with <hashed-secret>
  Note over Service Provider,Payment Gateway: Payload( P, <hashed-secret> )
  Payment Gateway->>Service Provider: Thx. Here's the secret
  Service Provider-->Payment Gateway: ** SILENCE **
  Payment Gateway->>L1: Cash cheque commitment with secret
  Service Provider->L1: Service Provider sees Payment Gateway's secret
  Service Provider->>Service Consumer: Here's the secret
  Service Consumer->>Service Provider: Here's the 10.2$ cheque
```
Payment Gateway deems Service Provider unreliable and closes the account.

### Multi-cheque 

We use Channels to handle mutliple unresolved cheques simultaneously.
This prevents channels being blocked during resolution.
Consider the case that: 

1. Service Consumer pays Payment Gateway via Service Provider and then Dennis before resolving the first cheque.
    2. And the cheque to Payment Gateway resolves before or after Dennis. 
    3. Or the cheque to Payment Gateway fails to resolve.  

TODO
