# nba-picks-record

A public, timestamped record of every slate decision made by a private NBA picks model. The model decides on full game moneyline and spread bets only, on paper, from a fixed set of public data. This repo holds the decisions, not the model.

## What is here

Every poll of the live pipeline, about every 15 minutes on game days, writes one record under `records/YYYY/MM/DD/`:

- `<time>.json`: every game on the day's slate and the next day's. For each game: the model projection, the pick (market, side, line, price, book, time of the quote, confidence, stake) or the reason there is none, and the anchor market at record time. Bet and no bet alike. The field `prev_sha256` is the hash of the previous record, so the records form a chain.
- `<time>.json.tsr`: an RFC 3161 timestamp token for the record from a public timestamp authority (DigiCert, or FreeTSA as a fallback). It binds the record hash to the second it was issued.
- `<time>.json.ots`: an OpenTimestamps proof. The calendars fold the hash into a Bitcoin transaction within hours. Until then the file holds the calendar receipts, and the nightly job upgrades it to the Bitcoin attestation.

A record proves that the decision existed at the stamped time. It does not prove a bet was placed. The ledger is paper.

## Decisions

| Decision | Meaning |
|---|---|
| `BET` | A paper bet was placed. The `pick` field has the details. |
| `NO_BET` | The model found an edge but the confidence score was below the bar. |
| `NO_PICK` | The model scored the game and found no edge under the policy. |
| `NOT_SCORED` | The game had no projection yet, for example the next day's slate before its decision time. |

## Verify a record

You need `openssl` with the `ts` command and the OpenTimestamps client (`pip install opentimestamps-client`).

```sh
python3 verify.py records/2026/11/07/2026-11-07T15:00:00Z.json
```

The script checks four things: the record's sha256 against the chain, the RFC 3161 token against the authority root in `ca/`, the OpenTimestamps proof (prints the Bitcoin block height once the proof is upgraded), and that the pick times inside the record precede tip. Pass `--all` to walk every record and check the chain end to end.

To check the Bitcoin anchor without a node, run `ots info <file>.ots`, read the block height, and compare the final digest to the merkle root of that block on any block explorer.
