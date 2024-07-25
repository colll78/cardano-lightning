# Demo: aims and objectives

## Document aims 

+ problem statements that the app addresses
+ break down of problem statements into feature set
+ feature set sketched out into an interface

## Context 

Cardano lightning is p2p payment solution built over the cardano blockchain.
Users of the network maintain two party channels, through which they can send and receive funds.
We refer to the participants of the channel as the party and counter party.

A user can perform various high level actions, including: 

1. Open, maintain, and terminate a channel
2. Send, receive, and resolve funds

We'll refer to all these and related activities as **network management** and **channel management**. 

We anticipate that there are different types of users of the network, 
characterized by their typical behaviour: 

+ a user who mainly sends funds
+ a user who mainly receives funds
+ a user who routes funds

Note, however, these distinctions are not strict.
Any user can send, receive, and route funds.
Nonetheless, we anticipate these characterizations relate 
to the preferred behaviour and tooling engaging the network.

A mainly-sends user is not necessarily technical and desires channel management via an intuitive mobile or web app, which is mostly offline until the user is active. 
A mainly-receives user may have some technical understanding, and desires lightweight channel management that integrates with existing software.
A mainly-routes user is probably technical and desires robust, HA software, where intuitive interface is secondary to powerful API/SDK. 

## Problem statement

> A network and channel management solution for the mainly-sends user. 

Capabilities requiring read and/or write to the L1:

1. Open a channel
2. Add/Sub from a channel
3. Mutually end a channel
4. Unanimously close a channel
5. Contest a close

Each of these requires the ability to query the current state of channels. 
It is also important that a channel history is available to the user. 

At least initially, the network has no shared global state. 
For each user, the L2 is simply the state of the channels of which they are a party. 

Capabilities requiring only the L2:

1. Liaise a secret commitment
1. Send a cheque with or without a commitment 
2. Receive a cheque
3. Resolve a cheque with or without commitment

Additionally, the user must be able to see the status and history of the L2.
The software prevents a user undertaking an action that puts their funds at risk, 
such as allowing the counter party to potentially over-leverage their account.

## Feature set

Organised loosely in the direction of pages

### Network management

1. Overview of status of channels
2. Filter/sort by user by state (open/closed/ended/alerts _etc_)
3. Add new channel
4. Respond to request for action
5. Store secret for unlocking

Other:

1. Data backup
2. Secrets backup

### Channel management

1. Overview of current L1 and L2 state with sync timestamp
2. Detailed history of L1 and L2
3. Perform relevant single party L1 operations
4. Request action from counter party for two party L1 operation
5. Send cheque with secret 
6. Resolve cheque with secret


## Reduced problem statement

### Blackboxed L1 api

Before wee write the plutus script(s), tx building functions and setup chain indexers,  
lets have an interface modelling the L1.

Here's a proposal:

```yaml
"/open": 
  description: |
    Opens channel between parties A and B with quantities `qa` and `qb` respectively.
    Returns channel id
  params:
    pka : PubKey 
    pkb : PubKey
    qa : bigint
    qb : bigint
  response: bech32
"/status": 
  description: |
    Get current value of channel.
    In the case that the channel does not exist or has been closed, then fail. 
  params: 
    id: bech32
  returns:
    qa: bigint
    qb: bigint
"/history": 
  description: |
    Get a list of all previous updates to state
    In the case that the channel does not exist or has been closed, then fail. 
  params: 
    id: bech32
  returns: History
"/add": 
  description: Add funds to your an account
  params: 
    id: bech32
    q: bigint
"/sub": 
  description: | 
    Remove funds from other account.
    Requires a signed state, own signature.
    Optionally an additional cheque, or and unresolved cheque with proof secret.
  args: 
    state: SignedState
    cheque: Cheque?
    proof: Proof? 
"/end": 
  description: |
    Both parties agree to end the channel.
    The channel is immediately terminated.
  args: 
    state: SignedEndState
"/close": 
  description: |
    One party closes the channel
  args: 
    state: SignedEndState
    cheque: Cheque?
    proof: Proof?
"/counter":
  description: |
    Counter party may endorse or contests the state present by the close.
    The channel is terminated.
"/finish":
  description: |
    If a channel is closed and no counter is submitted during a time window, 
    then the channel can be unanimously terminated.
```

TODO: 

- [ ] Complete this api into a compliant openapi schema. 
- [ ] Specify the datatype and signatures.
- [ ] Draw a lifecycle diagram for the L1
- [ ] De-prioritize close, counter, finish

## Reduced feature set

### Network management

  1. View existing channels. Click to open channel manager with channel 
  2. Open new channel 
  3. View requests

### Channel management

  1. View L1/L2 status 
  2. View L1/L2 history
  3. Do add, sub
  4. Request end
  5. Send cheque
