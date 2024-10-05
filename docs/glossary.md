# CL Glossary 

## About 

A simple way to collect terms in one place that we use across the project. 

This is exclusively for terms that are used in way with distinct or precise meaning, 
not shared by an established context.
For example, it includes 'channel' and 'account', but not 'utxo'.

Insert a new term in its alphabetic order. 
Prefer:

- lower case by default although upper case is allowed. 
- verbs in their infinitive (without 'to')

In each entry, link the first occurrence of mentioned terms with relative anchors.
Assume that the anchor ref is header with all punctuation and spaces replaced by single hyphen characters `-`.

## Terms 

### account 

The value of [channel](#channel) attributed to one of its [participants](#participant).
Typically this is represented by a single positive integer, 
since channels are mono-asset. 

### add 

A [step](#step) on a [live](#live) [channel](#channel) that increases the value of one of the [accounts](#account).

### cease

Any terminal [step](#step) ceases the channel.
A [channel](#channel) that no longer [exists](#exist) is ceased.

### close 

A [step](#step) that changes the [phase](#phase) from [live](#live) to [dead](#dead).

### channel 

The fundamental link between two [participants](#participant) in the CL network. 
A channel (that [exists](#exists)) consists state on both the L1 and L2. 
It includes two accounts, one for each participant.

### dead 

The second [phase](#phase) of channel after a [close](#close).

### end 

A [step](#step) to a [dead](#dead) [channel](#channel) in which it [ceases](#cease). 

### exist

A [channel](#channel) exists if it there is utxo that represents it on tip.
See also [cease](#cease)

### open

A [step](#step) that initially makes the [channel](#channel) [exist](#exist) and [live](#live).
The participant (assumed singular) who creates and submits the transaction.

### live 

(Adjective.) The main [phase](#phase) of channel.

### participant 

Anyone using the CL network.

### phase

A [channel](#channel) phase relates to it's L1 state. 
A channel (that [exists](#exist)), begins in a [live](#phase) then later [steps](#step) to a [dead](#dead) phase.

### step

A Cardano transaction that either spends and/or outputs a utxo representing a [channel](#channel) 
is said to step the channel. 

The term is used both for a specific step, and to mean a "type of step". 
For example, we may say: 

- "this tx steps this channel" or
- "add is a step"

Steps include: [init](#init), [add](#add), [sub](#sub), [close](#close), [end](#end)

### sub 

A [step](#step) on a [live](#live) [channel](#channel) that decreases the value of one of the [accounts](#account).
The channel remains live.
