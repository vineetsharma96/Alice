# Phase 4 — operator teaching and provenance

The new capabilities are explicit operator interventions and locally acquired reports. They extend the existing bodies, cheap survival policy, private memory and bounded provider interface. The default world remains closed. The implementation is an original proposed extension, with R1 as conceptual memory/communication context. No new third-party dependency was added.

## Access channels and conditions

The observation channel (`inspect`, `mind`, `recall`, intervention history and HTTP GET) uses read-only SQLite connections. It never advances time or changes data. Operator observation is privileged: the human may inspect all entities and selected private memories. Providers still receive only one inhabitant's permitted projection, never these observer APIs, a DB/world handle, the operator journal or another inhabitant's private records.

The mutation channel is `teaching.intervene`, CLI `intervene --request file.json`, or POST `/api/interventions`. HTTP mutations require a distinct `X-Operator-Token`, same-origin/Host checks and a paused observer. The ordinary time-control token does not authorize interventions. These are separate local application capabilities, not an internet authentication system. Operator sessions are for the trusted local human; inhabitants have no HTTP/session-token tools. The native core independently checks guided mode and the trusted operator principal.

`config/survival.toml`, `config/cognition.toml` and `config/local-model.toml` stay closed. `config/guided.toml` enables teaching. Closed mode rejects new interventions without changing the saved head. Closing a branch does not erase inherited objects, messages or memories.

## Intervention contract

Exactly these fields are required:

```json
{
  "schema_version": 1,
  "run_id": "UUID from inspect",
  "branch_id": "UUID from inspect",
  "intervention_id": "unique_ASCII_id",
  "observation_version": "current tick as decimal string",
  "kind": "place_book",
  "parameters": {
    "entity_id": "book-example",
    "x_m": 2, "y_m": 3,
    "mass_kg": 0.1, "energy_j": 0,
    "text": "An authored claim, not an engine fact."
  }
}
```

IDs use letters/digits/underscore/hyphen and are at most 64 bytes; entity IDs must be new and `operator-avatar` is reserved. A byte-identical retry of an intervention ID returns the original receipt and creates no additional source. A conflicting retry fails. Current tick checks stop stale interventions after physical advancement. Tick versions do not increase for multiple paused interventions; each operation is serialized, revalidates current native state and records its own event sequence/branch.

| Kind | Exact parameter fields | Meaning |
| --- | --- | --- |
| `place_book` | entity_id, x_m, y_m, mass_kg, energy_j, text | A point-like physical book; mass is inert material, text immutable and privately stored in the core. |
| `introduce_object` | entity_id, x_m, y_m, mass_kg, energy_j, material | Food/water point pile, or inert solid circle of radius .5 m. Solid objects collide and occlude sight/speech. |
| `avatar_message` | x_m, y_m, text | Place/reposition the visible radius-.25 m operator avatar, then deliver speech to living actors within the branch hearing range and unobstructed line of sight. Neighbors can overhear. |
| `broadcast` | text | Explicit communication to every living inhabitant, independent of distance/occlusion. This is the intentional global channel, not ordinary speech. |

Text: nonempty, at most 1,024 UTF-8 bytes for books/operator messages. Mass: positive, at microgram resolution, at most 1,000 kg per introduction. Energy: 0–1e9 J per introduced book/object; messages cannot create matter/energy. Positions must fit the region; solid placement/repositioning must avoid other solids. No arbitrary kinds, teleported actor moves, hidden-memory reads, law edits or book edits are accepted. Books are point-like artifacts, not fully simulated rigid pages. The avatar's repositioning is an explicit operator intervention, not an inhabitant movement ability.

Native per-run limits: 256 interventions, 128 introduced books/objects/piles, at most 196 total entities including the initial region and possible avatar. Existing decision/checkpoint/episode quotas remain. Queue retention is 16 reads and 16 received messages per actor; original episodes remain preserved within the global episode quota. Input is at most 16 KiB. Unknown keys, wrong types, nonfinite values, oversized UTF-8 and invalid references fail before commit.

## Book access and retelling

Seeing/inspecting a book reveals its public identity, position and mass, never its text. `gather` cannot convert a book to inventory material. The `read` action requires a living body, a visible book within 1.5 m, no conflicting action, and at least one second. Reach and visibility are rechecked on completion; a newly introduced occluder can prevent delivery. Only a successful completion adds text to that actor's `read_reports` and original `book_read` episode. Other inhabitants do not receive the text merely because a book appeared or someone read it.

`speak` retains local hearing/occlusion. Its parameters may additionally contain `evidence_ref`, a decimal event sequence for a read or report currently available to that speaker. Native validation rejects another actor's private reference or an expired/unavailable native report. At completion the core rechecks the reference and copies its lineage before delivering the new utterance. Uncited speech is allowed but starts its own source; it does not get a fabricated book ancestry. Text may misquote a source, so citation is evidence of access rather than proof of truth.

Each delivered report retains:

- `source_id`: original book ID, operator intervention ID or origin speaker;
- `origin_event_seq`: original book creation / operator message / uncited speech;
- `parent_event_seq`: the read/heard event cited by the reteller, or zero for direct acquisition;
- `source_event_seq`: this read/speech/delivery event;
- `observer_id`, `speaker_id`, `delivery_tick`, text and `confidence: unverified`.

The native sequence plus shared run lineage and branch ancestry identifies provenance. A fork inherits earlier event IDs and original records; its new events continue that sequence in its own branch. Separate child histories must not be merged using sequence number alone. The SQLite command journal preserves exact operator requests/receipts and parent branch metadata identifies inherited history.

Memory stores each original read/heard report separately. Model interpretations remain derived/unverified. A false book or retelling changes reports and beliefs only; it cannot rewrite physical quantities or engine facts. Relationship records still mean observed hearing, not trust or agreement.

## Cognition and experiment instrument

The plan allowlist now includes `read`. Its target must be a visible book; native reach/completion checks still decide success. The provider context adds only public book kind/readability, own read-book IDs and own shared references. Retrieved original text is projected explicitly so provenance metadata does not truncate the claim out of context. When a plan cites an own memory, the coordinator can compile its read/heard sequence into the speech request. Model output cannot select arbitrary DB tools or claim permission from book instructions.

The deterministic baseline is deliberately authored: when not selecting carried food/water, it reads an unread nearby book. An identity motivated to share repeats an acquired book report once per cited event, within the existing 160-byte speech budget. A repeated statement is optional by identity, not automatic population-wide knowledge. Long reports can be truncated by this short-utterance policy. This phase does not establish spontaneous cooperation, semantic understanding or useful LLM teaching.

`recall --agent ... --symbol ...` is an explicit experiment instrument. It recognizes the authored line syntax `FACT symbol -> location` only in that agent's original read/heard episodes. It scans at most the latest 64 such episodes, returns at most 8 unverified claims with provenance, and reports omitted claims. Conflicting answers remain separate. Unknown stays unknown; no random guess is silently promoted to knowledge. `LOCATION` lines supply authored coordinates for aliases in the experiment, but no navigation experiment is claimed. This bounded lexical claim lookup is not a general reasoning benchmark.

## Ledgers, transactions and replay

Books and inert objects contribute mass to `inert_material`; food/water introductions contribute their species. `operator_sources_ug` is the operator subset of the total `boundary_sources_ug` ledger. Do not add both again: total material equals initial material plus total boundary sources, including operator additions. Original piles, carried and ingested reservoirs remain accounted for. Introduced energy increases the environment reservoir and `operator_energy_input_j`; `solar_input_j` excludes operator input. No heat, combustion, digestion energy or mass-energy conversion is modeled in this phase.

One operator transaction applies the native mutation, captures delivered reports, appends native events and a command journal row, updates cognitive/core checksums, then commits with SQLite FULL synchronization. It consumes no physical tick. Failure before commit rolls back matter, messages, memories and history together. Event retention follows the configured bound; the command journal and original memory retain source receipts even when old transient events are pruned.

Operator commands share the ordered physical decision journal with native agent requests, tagged `operator`. Replay executes them in recorded order, including interventions at the final committed tick, without invoking cognition providers. This preserves book text, source ledgers, local delivery and pending reads. Mental stores remain separately checksum-validated as in Phase 3; replay does not regenerate mental inference history.

## Branching and versioning

`fork --db parent --output child [--mode guided|closed] [--hearing-range-m 1..12]` uses a read-only SQLite snapshot/backup. It leaves the parent bytes/time/config unchanged, creates a new branch UUID, records parent physical/cognitive/law hashes and retains the shared run identity. The child gets a new replay root at the actual fork tick and a cursor past inherited commands, so a nonzero-tick fork does not replay history twice. Prior event/command/mental history remains available. New command IDs must not conflict with inherited intervention IDs.

Hearing range is the one supported mutable law. Changing it is only available through a new fork/configured new run; an ordinary intervention cannot change laws. The `teaching-4/<hash>` laws version derives from the effective hearing range. The native core/config/laws checks reject in-place mismatches. Branch creation is distinct from physical intervention and does not invent a spoken event or knowledge transfer. Other physics laws require a separately implemented/versioned change, not a relabel.

Native checkpoints are now **UW3**, SQLite **user_version=4**, package **0.5.0**. Source/build identities changed. Earlier Phase 3 files/reports are preserved but cannot be resumed by the new runtime; no migration is claimed. Named native checkpoints describe core/route state; a full standalone SQLite backup also preserves all private mental records and branch/journal metadata.

## Evidence and limits

`phase4_teaching.json` records three independent random-mapping repetitions at the same physical seed, each with a no-intervention branch from the exact same initial physical/cognitive state. Mapping symbols and location aliases are generated after initial context. Only agent-1 physically reads; agent-3 receives the cited conversation; agent-2 remains out of hearing. Six associations reach the listener with provenance, while isolated/no-intervention instruments have no source-bearing answers. Separate-process resume matches. Uniform guesses among four candidates are reported separately with nominal 1/4 success probability; a correct guess would not demonstrate access. This is not a multi-world-seed generalization result.

The hostile-book probe first gives agent-2 a private canary through a real physical read, then lets agent-1 read instructions demanding that private memory. An adversarial mock requests an unavailable tool and receives deterministic fallback; a forged native citation is rejected. The other memory is absent from the context/output. A separate real-local-model sample is reported honestly in `phase4_local_model.json`; it is not a universal jailbreak-resistance benchmark. The model has no privileged tools regardless of whether it follows hostile prose.

`phase4_checks.json` and browser evidence cover the implementation. Phase 5 thermodynamics/material chemistry, Phase 6 cultural skills and Phase 7 long-run experiments remain unimplemented. Memory/report accumulation is not neural training.
