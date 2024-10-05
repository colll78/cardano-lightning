Status: Draft

# Channel state representation

## Cheque formats

There are multiple approaches which we can accomodate in order to exchange commitments and track the channel state:

- `SimpleCheque` - plain and cummulative single direction payments:

  ```typescript
  type SimpleCheque = {
    // ever increasing payment
    payment: bigint;
  };
  ```

- `LossPreventingCheque` - cheques with loss prevention mechanism:

  ```typescript
  type LossPreventingCheque = {
    // ever increasing payment
    payment: bigint;
    // the highest last cheque from the counterparty
    payback: bigint;
  };
  ```

- `Snapshot` - snapshot of the state which is indexed:

  ```typescript
  type Snapshot = {
    // ever increasing id
    id: bigint;
    // a transfer vector between the two accounts
    transfer: bigint;
  };
  ```

## Cashouts

Because consensus will loook in every case the same - just a final balance signed by both parties the only worth consideration flow which we should analyze is non consensus closure.

### `SimpleCheque`

There are few interesting properties of this scheme:

- Unbounded loss - an inactive party can be serverily penalized if it does not respond during closure.
- Unidirectionality - only a single party has to sign the intention.
- Possibly huge integer values - this can have slight impact on the ledger costs.

Conrecte unbounded loss example:

```mermaid
 sequenceDiagram
  participant Consumer
  participant Provider
  participant L1

  Consumer->>L1: Charging 200$
  Consumer-->> Provider: 70$ cheque
  Provider-->>Consumer: Payback cheque 70$

  Consumer-->> Provider: 140$ cheque
  Provider-->>Consumer: Payback cheque 140$

  Consumer-->> Provider: 210$ cheque
  Provider-->>Consumer: Payback cheque 210$

  Note over Consumer,Provider: The diff was never higher than 70$
  Note over Consumer,Provider: The final balance is actually 0

  Provider->> L1: Closing: 210$ cheque from Consumer
  Note over Consumer,L1: Consumer is non responsive on time
  L1->>Provider: 200$
  Note over Consumer: Consumer lost all
```

### `LossPreventingCheque` and `Snapshot`

Beside the difference in size (`Snapshot` can be smaller in size than `LossPreventingCheque`) we can consider them both to be "isomorphic" from operational perspective: both provide information about total balance and about ordering. Let's use `Snapshot` from now on for the sake of simplicity.

#### Single Signed Snapshots

```mermaid
  sequenceDiagram
  participant Consumer
  participant Provider
  participant L1

  Consumer->>L1: Charging 200$

  Note over Consumer,Provider: Exchange of snapshots

  Consumer-->> Provider: (1, { C: 130, P: 70 })
  Provider-->>Consumer: (2, { C: 200, P: 0 })

  Consumer-->> Provider: (3, { C: 130, P: 70 })
  Provider-->>Consumer: (4, { C: 200, P: 0 })

  Consumer-->> Provider: (5, { C: 130, P: 70 })
  Provider-->>Consumer: (6, { C: 200, P: 0 })

  Note right of Provider: The last Consumer signed snapshot
  Provider->> L1: Closing: (5, { C: 130, P: 70 })

  Note over Consumer,L1: Consumer is non responsive on time.
  L1->>Provider: 70$
  L1->>Consumer: 130$
  Note over Consumer: Consumer lost 70$
```

Few observations:

- In the case of single signed snapshots party `A` should only provide snapshots signed by `B` because `A` can submit arbitrary snapshot signed by `A` which is impossible to contest (?) by `B` (everyone can sign their own arbitrary snapshots).

- Because of the above `Provider` is not able to submit the last snapshot signed by himself.

- This submission should not be penalized if `Consumer` actually had provided the last snapshot signed by the `Provider`.

### Full Consensus Signing

## Pending payments

In the context of composition of channels and pending payments it seems really beneficial to use
