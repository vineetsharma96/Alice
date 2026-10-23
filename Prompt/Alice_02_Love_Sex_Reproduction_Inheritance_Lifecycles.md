# ALICE 02 — Love, Biological Sex, Reproduction, Inheritance and Generations

## Mission and boundaries

Continue https://github.com/vineetsharma96/Alice. Extend existing emotional inhabitants into a persistent population with individual relationships, developing love-like attachment, biological reproduction, offspring development, inheritance, aging and demographic change. Include species-appropriate reproductive systems for plants and animals, coordinated with the plant/seed contracts in prompt 01 and microbial populations in prompt 03.

Read AGENTS.md, README, HANDOFF, current contracts/status, emotional implementation, learning/communication and biology code before edits. Verify the user's reported completed emotions against actual runtime behavior. Record commit and baseline results. Preserve existing worlds and research evidence. Do not invent capabilities to satisfy prerequisites, rewrite the engine or reset worlds at agent handoff. These are software models of behavior, not evidence of subjective love or consciousness.

Implement one shared lifecycle/lineage framework with species-specific reproductive strategies. Do not run separate competing birth or mortality systems. Keep this feature independent enough to test with minimal fixtures if prompt 01 is incomplete, while integrating with actual world resources for the final demonstration.

## L0 — Audit, time model and durable contracts

Inventory ages, sex fields, emotion state, relationships, goals, needs, learning, death, identity allocation and save/replay. Specify biological time in relation to world time and seasons. Reproductive maturity, gestation, growth and aging must follow one declared scale per species. Do not silently make a human age decades during a weather day. Long-life evaluation can use an explicit accelerated calendar and report its limitations.

Define SpeciesLifecycle, ReproductiveProfile, LifeStage, Lineage, RelationshipEvidence, PregnancyOrIncubation and CareCommitment contracts, adapting names to the codebase. Keep stable identifiers after death. Use transactional birth IDs and single-application event semantics to prevent duplicate newborns during replay or retry.

Gate: versioned contracts, baseline, migration decisions and evaluation protocol exist; no current save is overwritten.

## L1 — Male/female biology and gender identity

Support male and female biological reproductive profiles for humanlike inhabitants and applicable animal species. Store reproductive role/physiology separately from gender identity. Include male and female identity options as requested, with unknown/unassigned state where appropriate. A broader identity representation can be extensible without requiring a complex identity simulation now.

Biological compatibility determines reproductive mechanics; identity does not dictate strength, intelligence, empathy, jobs, leadership, caregiving or personality. Gender identity and reproductive physiology are not the same field. Do not claim identities emerge independently if initialized by configuration. For existing adults, migration or operator configuration must transparently declare any newly seeded attributes rather than pretending they had always developed them.

Plants may have both reproductive functions or separate male/female individuals depending on their species. Bacteria-like organisms may divide asexually. Do not force male/female pairing onto all life. Abstract reproductive actions are sufficient; explicit anatomical or sexual animation is unnecessary.

Gate: applicable species use valid reproductive profiles, incompatible combinations cannot bypass mechanics, and sex does not secretly alter unrelated competence scores.

## L2 — Experience-based attachment and love-like behavior

Build on the existing emotion framework. Represent directional familiarity, trust, affection, attraction where supported, attachment, relationship satisfaction and expectations with uncertainty and evidence. Avoid a universal scalar love meter that automatically triggers reproduction. Distinguish friendship, kin attachment, caregiving bonds and romantic interest.

Relationships can grow through repeated reliable assistance, shared activities, communication, responsiveness and experienced safety. Encounter opportunities must arise from actual proximity, time and actions. Individual preferences can develop from experience; initialize any predispositions explicitly. Repeated proximity alone does not prove trust or romance. No access to another's private feelings, memories, attraction or intentions.

Allow affection to influence spending time together, requesting/accepting help, remembering a partner's observed preferences, sharing costly resources, joint planning and repair after conflict. Costs are real inventory/time/energy costs. Do not script a guaranteed partner for every inhabitant, assign love solely by compatible sex or make reciprocal love automatic. A can love B without B reciprocating. Some inhabitants may never form romantic bonds.

Separate known affection from uncertain beliefs about reciprocation. Courtship/relationship invitations and their acceptance/decline need explicit action semantics for mature autonomous inhabitants. Respect declined invitations and bound repeated retries. A relationship does not grant permanent consent to all future commitments. Learning and emotion can modulate choices but must not bypass another agent's action authority.

Gate: different encounter histories create different attachment/help-seeking preferences; disabled relationship learning weakens that history dependence; distinct people retain different responses; declined relationships do not become silently reciprocal.

## L3 — Partnerships and joint intentions

Support optional mutual partnership commitments acquired through interaction and communication. A shared plan must contain each participant's individually accepted commitment rather than one controller commanding both. Keep ordinary cooperation possible without romance, and romance possible without reproduction.

Relationships may strengthen, weaken, end or be repaired. Emotional responses depend on private expectations and evidence, not global labels such as 'betrayer'. Do not force jealousy, aggression or gendered roles. Existing invented language should carry learned social signals; do not install a universal romance vocabulary. Observer labels can remain English while agents' symbols are private learned conventions.

Gate: partnerships require two valid decisions, persist through save/resume, and can end without corrupting kinship or ownership data.

## L4 — Reproductive mechanics

For humanlike inhabitants, enable abstract reproduction only among mature compatible adults with independently accepted current reproductive intentions. Require proximity, feasible bodily conditions, reproductive availability and a species-configured probabilistic conception model. No conception from mere romance score, co-location or an operator drawing a heart. Babies, juveniles and adults must be distinct stages; immature individuals cannot enter reproductive actions.

Model pregnancy/gestation or egg formation/incubation, energy/nutrient requirements, carrying costs, elapsed biological time, birth/hatching and postpartum/refractory intervals where appropriate. Repeated requests within one time step cannot create multiple simultaneous pregnancies. Unfertilized eggs used as food remain distinct from viable embryos. Birth transfers actual biological resources and must not duplicate parent reserves.

Nonhuman animals use species-specific mating/readiness and behavioral rules, not human partnership semantics. Existing care systems must continue to supply food and water throughout gestation and development. Plants use flowering/pollination/seed contracts from prompt 01, never a second seed-spawn loop. Microbial reproduction belongs to prompt 03 but must use compatible accounting/lineage events.

Gate: valid births/hatches occur after required elapsed time and costs; invalid or immature pairings are rejected; save/load mid-gestation yields no duplicate birth; scarcity influences outcomes transparently.

## L5 — Inheritance, variation and cultural separation

Implement a small explicit trait schema with recombination or a documented simplified inheritance model, bounded mutations and per-trait ranges. Candidate traits: body size potential, metabolic efficiency, maturation/longevity tendencies and sensory sensitivity. Initial personality/temperament may include bounded inherited predispositions only if declared and evaluated; avoid treating learned values or morality as genetic facts.

Record parents, lineage, inherited components and mutations. Never copy parental episodic memories, complete lexicons, tool knowledge, emotional associations or established relationships into newborns. A newborn may have declared innate drives and age-appropriate capabilities. Skills and language require developmental experience, imitation or teaching. Separate genetic inheritance, individual learning and cultural transmission in storage and reports.

Parenthood does not instantly create mutual trust or perfect care. Kinship can be authoritative lineage metadata for observers while agents learn family identity through implemented perceptions/communication. Implement a declared close-kin reproductive compatibility rule for humanlike adults rather than accidental unrestricted pairing; document any simplified observer-level biological rule separately from what agents know. Do not add elaborate genetic disorders to imply realism without evidence.

Gate: offspring show traceable bounded inherited variation across seeds, remain distinct individuals and do not inherit a secret copy of parental knowledge.

## L6 — Development and caregiving

Life stages: newborn/hatchling/seedling as appropriate, dependent juvenile, adolescent or pre-reproductive stage, mature adult and later-life stage. Use gradual capability changes where feasible rather than a timer that unlocks all knowledge. Separate movement capacity, digestion/food access, perception, work limits and learned skill.

Dependent offspring need feasible care: feeding, warmth, protection and age-appropriate teaching. Humanlike care can be provided by accepted caregivers regardless of sex. Allocate actual resources and interrupted work. No invisible supply feeding offspring. Extend existing goals so caregivers notice recurring needs, balance their own survival and request assistance. Bounded authored care baselines are allowed but must be labeled, not claimed as learned parenting.

Gate: juveniles develop under supplied care, deprivation has modeled consequences, multiple caregivers can coordinate without double-feeding, and skills require demonstrated learning.

## L7 — Aging, death and emotional consequences

Implement species-configured age-dependent changes in function and mortality hazard. Use rate-aware hazard sampling, for example probability derived from hazard times elapsed biological time, instead of per-tick death chances that change with frame rate. Old age is not universal simultaneous death at one hard birthday unless explicitly a simplified species rule.

Death finalizes active work, inventory/body material, gestation and care responsibilities consistently. Emit organic substrate events for prompt 03; keep a clearly owned temporary fallback if microbes are absent. Preserve historical identity and lineage with bounded storage. Decay does not erase records of a person from others' memories.

Attachment-dependent grief-like responses must follow perceived loss, not immediate remote access to a death event. Support uncertainty if someone is absent. Recovery and social help can occur without instant deletion of attachment. Do not force every death to create grief in every inhabitant.

Gate: age statistics match the declared model; deaths produce accounted outcomes; close companions and strangers respond differently based on known history; remote private loss does not leak.

## L8 — Population dynamics and generational continuity

Track births, deaths, age/sex structure where applicable, family/partnership networks, resource demand, recruitment, care burden and lineage diversity. Carrying capacity should emerge from resource/habitat constraints and modeled choices, not a hidden routine killing excess people.

For computation limits, pause/checkpoint explicitly or reject an experiment configuration before launch. Never secretly cull offspring, convert live people to a count, spawn partners to fix demographics or replenish food. Cohort aggregation is appropriate only for explicitly aggregate species and must conserve their modeled stocks. Extinction or stagnation is a valid experimental outcome.

Gate: multi-generation trials run without hidden demographic rescue; demographic events reconcile to population totals; resource scarcity and improved care produce interpretable differences.

## L9 — Persistence, viewer and evaluation

Persist relationship evidence and uncertainty, biological state, genetic traits, pending births, care plans, learned developmental state and lineage. Seed random streams so replay cannot change parentage or birth outcomes arbitrarily. Provide observer panels for relationship directionality, causes of attachment, demographic timelines, life stages, lineage and care deficits. Do not give inhabitants observer-only graphs.

Before tuning define dev/held-out worlds, thresholds and paired controls: relationships frozen/disabled, emotions disconnected from decisions, care disabled where ethically irrelevant to real beings but computationally diagnostic, genetic variation disabled and teaching unavailable. Keep initial resources comparable. Use several seeds and report per-run evidence. Include save/resume mid-pregnancy and mid-care, declining a relationship, one-way affection, nonromantic cooperation, unknown loss, resource scarcity, family teaching and three or more generations where compute allows. Longer accelerated trials need explicit calendar assumptions.

Measure relationship prediction and history effects, shared-resource choices, valid/invalid reproductive attempts, birth rate, offspring survival, care fulfillment, age distribution, lineage variation, learning provenance and resource accounting. Do not select only a romantic success story. Failed attachment hypotheses or extinctions belong in the report.

Deliver integrated code, appropriate tests, raw evidence, exact commands, seed/configs, operations/migrations documentation and updated STATUS/HANDOFF. Clearly separate authored mechanics from acquired relationships. Implement L0-L2 first, validate, then proceed in order through L9. Do not stop at a plan or claim subjective love.

## References to inspect

- Alice: https://github.com/vineetsharma96/Alice
- FAtiMA appraisal/decision architecture: https://github.com/GAIPS/FAtiMA-Toolkit
- SELAgents social/emotional learning candidate: https://github.com/nicolastorresr/SELAgents
- Population ecology: https://openstax.org/books/biology-2e/pages/45-3-environmental-limits-to-population-growth
- Plant reproduction: https://extension.oregonstate.edu/catalog/em-9900-reproductive-plant-parts

Verify upstream code, commits and licenses before adapting anything; source access is not license permission. Do not add two competing emotion engines or assume repository claims have been independently validated.
