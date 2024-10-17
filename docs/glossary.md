# CL Glossary

## About

A simple way to collect terms in one place that we use across the project.

This is exclusively for terms that are used in way with distinct or precise
meaning, not shared by an established context. For example, it includes
'channel' and 'account', but not 'utxo'.

Insert a new term in its alphabetic order. Prefer:

- lower case by default although upper case is allowed.
- verbs in their infinitive (without 'to')

In each entry, link the first occurrence of mentioned terms with relative
anchors. Assume that the anchor ref is header with all punctuation and spaces
replaced by single hyphen characters `-`.

## Terms

### account

The value of [channel](#channel) attributed to one of its
[participants](#participant). Typically this is represented by a single integer,
since channels are mono-asset.

### add

A [step](#step) on a [opened](#opened) [channel](#channel) that increases the
value of one of the [accounts](#account). Note that this step does not change
the stage.

### channel

The fundamental link between two [participants](#participant) in the CL network.
A channel (that [staged](#staged)) consists state on both the L1 and L2. It
includes two accounts, one for each participant.

### close

A [step](#step) that changes the [stage](#stage) from [opened](#opened) to
[closed](#closed). It is performed by a [participant](#participant) who wishes
to end the [channel](#channel).

### closed

The second [stage](#stage). It occurs after a [close](#close) step. The
participants are no longer transacting off-chain (at least for long).

### elapse

A [step](#step) that changes the [stage](#stage) from [closed](#closed) to
[elapsed](#elapsed). This is performed by the participant who performed the
[close](#close) step. It can only occur if there has been a sufficient passage
of time since the close. The participant unlocks the funds owed.

### elapsed

A third [stage](#stage) of a [channel](#channel). It is the result of an
[elapse](#elapse) step. The remaining funds belong to other participant.

### end

A [step](#step) that [unstages](#unstage) a [resolved](#resolved)
[channel](#channel). The participant that performed the [close](#close) unlocks
their funds.

### funds

The preferred term for assets in the channel that are locked as collateral on
the L1. Use the term 'funds' over alternatives such as 'value', 'assets',
'tokens', _etc_.

### life-cycle

In relation to a [channel](#channel), it is the series of [steps](#step). (This
term is include mainly to document that the preferred form is as two words
separated by a hyphen.)

### open

A [step](#step) that [stages](#staged) [channel](#channel) as [opened](#opened).
The [participant](#participant) performing an open locks their funds and
indicates the credentials of the other participant.

### opened

The main [stage](#stage) of [channel](#channel). While the channel is at this
stage, the [participants](#participant) are transacting off-chain.

### participant

Anyone using the CL network. In relation to a [channel](#channel), there are two
participants.

### recover

A [step](#step) that [unstages](#unstage) an [elapsed](#elapsed)
[channel](#channel). The participant that did not perform the [close](#close)
recovers their funds.

### resolve

A [step](#step) that changes the [stage](#stage) from [closed](#closed) to
[resolved](#resolved). This is performed by the [participant](#participant) who
did not performed the [close](#close) step. The participant supplies to their
summary of the off-chain transacting to the L1 and unlocks their due funds.

### resolved

A third [stage](#stage) of a [channel](#channel). The participant who did not
perform the [close](#close) performs a [resolve](#resolve) step where the
off-chain summary is provided to the L1. The participant unlocks the funds owed.

### stage

A [channel](#channel) stage relates to it's L1 state. A channel (that
[staged](#staged)), begins in a [opened](#opened) then later [steps](#step) to a
[closed](#closed) stage.

### staged

A [channel](#channel) is staged if it there is utxo that represents it on tip.
That is to say, it is staged if there is a utxo at tip representing its current
[stage](#stage). See also [unstaged](#unstaged)

### step

A Cardano transaction that either spends and/or outputs a utxo representing a
[channel](#channel) is said to step the channel.

The term is used both for a specific step, and to mean a "type of step". For
example, we may say:

- "this tx steps this channel" or
- "add is a step"

Steps include: [init](#init), [add](#add), [sub](#sub), [close](#close),
[end](#end)

### sub

A [step](#step) on a [opened](#opened) [channel](#channel) that decreases the
value of one of the [accounts](#account). The channel remains opened.

### unstaged

Any terminal [step](#step) ceases the channel. A [channel](#channel) that is no
longer [staged](#staged) is ceased.
