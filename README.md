# cardano-lightning

## Why Lightning?

- Secure: The integrity of the L1
- Near instant settlement
- Highly scalable

## Repo overview

Currently we use monorepo approach for creating the preliminary specification
and POC implementation. Later on we will split this into separate repositories.

This repo uses nix flakes.

```sample
$tree -L 1
.
├── bin           # helpers
├── docs
├── flake.lock
├── flake.nix
└── README.md
```
