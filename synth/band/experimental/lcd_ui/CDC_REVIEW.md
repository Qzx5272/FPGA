# LCD UI snapshot timing review

Candidate a: setup passed; 68 hold endpoints failed. Worst reported endpoints were `ui_cdc/held_*` → `ui_cdc/display_data_*`, about −0.52ns. Do not program a on the basis of that report.

The payload uses a bundled-data toggle handshake, not a continuously changing synchronous bus:

1. The source copies the state into `held` and flips `request` only when synchronized `ack2 == request`.
2. `request` traverses `req1` and `req2` in the pixel domain. The destination copies `held` only on a frame boundary and when `req2 != ack`.
3. The destination raises `ack` in the same edge as that copy.
4. `ack` traverses `ack1` and `ack2` back to the source. Only after this round trip can the source overwrite `held`.

Thus the source cannot change the payload at the destination's enabled capture edge or its hold window. Clock-to-clock same-edge hold analysis is not applicable to that enabled path. Its bounded max-delay/setup analysis is retained to ensure payload arrival before the synchronized request is consumed.

Candidate c applies hold exceptions only to these destination D pins:

```
set_false_path -hold -to [get_pins {ui_cdc/display_data*_s0/D ui_cdc/ack1_s0/D ui_cdc/req1_s0/D}]
```

The frozen netlist was checked: all 67 retained display_data D flip-flops have their D input directly connected to held bits. The exception does not cover reset or enable pins. The two other D pins are first-stage toggle synchronizers. Second-stage synchronizers, destination UI logic, audio paths, LCD outputs and all setup checks remain timed. Independent-clock tb_ui_state.sv checks frame-atomic capture and publication delay.

The exact synthesis netlist from a is reused with SHA256 verification, followed by conventional placement and routing. Candidate b attempted incremental routing but was stopped before a result; it was never programmed. Programming candidate c requires a fresh complete audit, with no waiver for other negative paths.
