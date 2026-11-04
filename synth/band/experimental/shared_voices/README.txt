Shared voice-bank allocation experiment — not the selected production engine.

Problem: the production band_core routes each role to one of eight32-slot banks.
This experiment separates musical role from physical bank. Every note-on first
probes all banks for the complete identity(source,contact,part,epoch,serial).
An existing identity is a duplicate. Otherwise a round-robin free bank receives
one commit. Only this router may issue allocator events; retirement may free
slots during probes, but no concurrent producer may consume a probed slot.
Off/source-release/part-release transactions are broadcast with unchanged payload.
Tail slots remain active until generation-checked renderer retirement. Panic
must be wired to both router and every allocator; it bypasses blocked traffic.

Validated by tools/test_shared_bank_dispatch.py with eight real32-slot allocators:
256 notes of one role/contact with unique serials; duplicate with full pool;
full rejection; released tails not stolen; correct retirement; stale serial and
generation protection; source/part release; panic mid-probe; a delayed completion
from bank7; unavailable-bank backpressure and payload immutability.
No renderer, acoustic output, synthesis, timing or real-board claim is made.

Integration still required before replacing production:
1. Every bank must retain parameters for all16 roles (current BANK_BITS indexing
   aliases roles); broadcast accepted controls and preserve smoothing/ownership.
2. All banks must support every renderer role, including choir. Current build
   enables choir arithmetic only in its dedicated bank. Measure cost; do not
   silently remove choir or constrain its allocation to claim shared capacity.
3. Lead-presence/role telemetry must aggregate by musical role across banks;
   bank6 activity no longer means lead activity. Keep causal accompaniment.
4. Route existing ordered ownership-release queue through this router; preserve
   priority panic and source loss. Validate scene changes and old note-offs.
5. Measure actual audio deadline, event throughput and resource/timing in the
   complete exported PT8211/DVI/singer workbench, then repeat bounded board gates.

Current published/Flash build59c963cc2112 remains unchanged and quota-based.
This candidate is not included in the already immutable V5.27 archive.

2026-10-26 update:
shared_voice_bank now has all16 role parameter sets;shared_band_renderer has
choir in every bank and applies stereo position per voice/role before bank sum.
This is intentionally not bank-dependent panning. Rounding occurs per voice,
so mixed/multi-voice aggregate PCM may differ from old bank-level panning.
Single-note all8role64sample reference comparisons and32choir64sample test pass,
maximum bank render960cycles at1042cycles/sample. Not long-term/fulltop proof.
shared_note_allocator exports actual active-role6 presence, including tails.
shared_band_core connects the ordered existing queue to two-phase dispatcher,
broadcasts controls, mixes bank stereo outputs and reports router rejection.
The core elaborates; integrated musical behavior/resource/timing not yet tested.
Evidence:shared_bank_dispatch/20261026_150523 and shared_voice_bank/20261026_150738.
The above integration to-do items now require behavioral and physical validation;
source implementation alone does not close them.

Actual hierarchy correction 2026-10-26:
Initial fulltop trial124aa1aed486 was invalid for shared capacity:physical top
uses band_singer_core, not band_core. Its synthesis/chain were stopped, and its
button pass applies only to the old quota path. Do not cite it as shared proof.
New shared_band_singer_core keeps dedicated part15 and atomically accepts
source broadcasts into both singer and shared-router paths. Actual singer-path
RTL test(shared_singer_core/20261026_152300) passes256choir slots plus electronic
singer for64samples,966max band cycles;both source releases and bar returns tested.
Corrected export c38c151eeea4/buildID3280737566 is under fulltop synthesis/chain.
prepare_shared_voice_trial now requires actual singer-core proof and verifies
that band_singer_core contains the shared bank instances. Physical acceptance
still pending; production V5.27 is unchanged.
