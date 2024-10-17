---
title: Partial Cash Outs and Additional Deposits
status: proposed
author: "@paluh"
date: 2024-09-08
tags:
  - deposit
  - cash out
---

## Context

### The Problem

Capacity of a channel or even asset balance in it determine how useful it can be
for the parties involved or for the network as a whole during the routing
process. It can be a pretty common situation that the channel is draied in one
direction so it can not be used for further payments. In such a situation it is
beneficial to recharge the channel with more assets to make it useful again. For
a hub operator there is a clear incentive to measure utilization of a the
managed channels and use that information to reallocate the assets between them
to increase the returns. So it seems that not only recharging but also cashing
out the channel capacity could be beneficial in such a case. Ideally we would
like to have a possibility to perform these operations efficiently and with a
minimal counter party interaction to facilitate batching.

### Operations Safety

If we consider deposit operation which increases channel account balance of a
party then we can see that this operation is by nature safe for the counter
party because it will not undermine guarantees of the current off-chain state
because L2 safety is based on the non decreasing liquidity locked in the channel
in the first place.

In the case of cash outs the situation is clearly more complex because any
decrease of the amount on L1 can make the current L2 state impossible to settle
on the L1. So it seems that cash outs should be carefully designed to not break
the L1 safety guarantees.

### Batching

Payment hubs could significantly benefit from batching of the discussed
rebalancing operations:

- Mixing charge operations and cash outs in the same L1 transaction can allow to
  rebalance the liquidity between channels in a more efficient way.

- Mixing partial cash outs or full closure together with charging or
  initialization of the channel could be considered as well.

### L1 and L2 Separation of Concerns

The core idea of Lighthing is to move as many transfers operations off-chain and
compress them to a concise final state representation which should be settled
down on the L1 level. This design creates pretty natural separation of concerns:

- L1 provides safety guarantees behind the liquidity which we operate on.

- L2 keeps track of the "current" state inside the channel.

This separation makes it easy to reason about the system state and its safety.

## Decision

- We will introduce `deposit` and `cash out` operations which can be performed
  during the channel lifecycle.

- Cash out approval signature will be an input to the `cash out` operation.

- We add two `cash out` id(s) for each party to prevent double cash out
  operations.

- We will rename the `account*` to `deposit*`:

  - We keep simple invariant
    `depositA + depositB = UTxO Value[channel asset class]`.

  - Instead of introducing separate `cash out` tracking variable we will allow
    negative account value which represents on `L1` a cash out above the account
    balance. It can be interpeted from `L1` perspective as a loan from the
    channel partner.

  - The first invariant should still hold so we know that at least one account
    has positive balance which covers a possible loan.

  - When a party with negative balance performs a `deposit` it naturaly pays
    back the loan first because we will increase the account balance and cover
    the negative value as a first step.

- The party `cash out` operation will consist of few checks:

  - Check of the counter party signature under the `cash out` approval.

  - Check if the `id` of the `cash out` is greater than the last stored
    `cash out` `id` for the party.

  - Check if the optional approval deadline is not exceeded.

### Rationale

- If we assume that the state on the L2 can be arbitrary then:

  - We can consider a situation that all the assets at the moment belong to
    party A.

  - If we allow party B to cash out any assets on L1 then we will have a
    situation where the L2 state can not be settled on L1 any more.

  So it seems that without operational restriction of the L2 we can not allow
  cash outs without counter party approval.

- Let's consider an L2 snapshot:

  - The smart contract has no way to instantly verify that a plain L2 snapshot
    is the latest one. Even if both parties agreed on it at some point in time
    it can be invalidated by the later state.

  - We could consider freezing of the L2 state. In such a case snapshots could
    be considered "fresh" up until the moment of some validity deadline.

  - Freezing the whole channel seems unnecessarily restrictive when we want to
    cash out only a part of the channel capacity.

Given the above properties it seems pretty natural to introduce "partial freeze"
which we call `cashout approval`. It is a signature under an amount and an
optional deadline which can be used to approve a cash out operation on L1:

- Up until the deadline the amount of the money should be considered as "frozen"
  and can not be used for further operations on L2.

- If the cash out is not performed until the deadline then the approval can be
  considered as expired and the funds can be used again.

- The approval can be used only once.

- An approval can be updated by preserving the `id` and increasing or preserving
  the deadline or the amount.

## Dissent, counter, and comments

TODO

## Consequences

TODO
