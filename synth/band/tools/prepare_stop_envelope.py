"""Prepare the timing experiment from the verified, routed singer-off baseline."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def prepare(source, output):
    manifest = json.loads((source / "manifest.json").read_text())
    if manifest["build_id"] != 0x20261108 or manifest["electronic_singer"]:
        raise ValueError("Expected the original singer-off baseline")
    hashes = {Path(name).as_posix(): value for name, value in manifest["source_sha256"].items()}
    output.mkdir(exist_ok=False)
    for name, expected in hashes.items():
        src = source / name
        if hashlib.sha256(src.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Source hash mismatch: {name}")
        (output / name).parent.mkdir(exist_ok=True, parents=True)
        shutil.copyfile(src, output / name)

    def change(name, replacements):
        path = output / name
        data = path.read_text()
        for before, after in replacements:
            if data.count(before) != 1:
                raise ValueError(f"Unexpected source in {name}: {before}")
            data = data.replace(before, after)
        path.write_text(data)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    # Router retains all payload fields until every addressed bank acknowledges.
    # Register the issue strobe and its probe/commit tag together; halt flushes
    # both the pending issue and the consumer on the original clock edge.
    change("rtl/band_singer_core.sv", [
        (" wire [16*59-1:0] patches;", """ reg [BANKS-1:0] issue_valid;
 reg issue_probe;
 always @(posedge clk)begin
  if(rst||halt)issue_valid<=0;else issue_valid<=allocation_valid;
  issue_probe<=allocation_probe;
 end
 wire [16*59-1:0] patches;"""),
        ("sample_tick,allocation_valid[b],bank_ready[b]", "sample_tick,issue_valid[b],bank_ready[b]"),
        ("   allocation_probe,allocation_done[b]", "   issue_probe,allocation_done[b]"),
    ])
    # Envelope inputs are latched in state 1. Overlap the shift/add and
    # select with oscillator computation, well before RAM writes in states 20/21.
    change("rtl/shared_band_renderer.v", [
        ("wire [16:0] musical_decay=", "reg [16:0] musical_decay; always @(posedge clk)musical_decay<="),
        ("wire [16:0] release_step=", "reg [16:0] release_step; always @(posedge clk)release_step<="),
        ("wire [15:0] decay=", "reg [15:0] decay; always @(posedge clk)decay<="),
        ("wire [16:0] attack_next=", "reg [16:0] attack_next; always @(posedge clk)attack_next<="),
        (" wire [159:0] next_voice_state={7'd0,harmonics,next_stage,noise[31:14],next_noise,next_envelope,gen,next_phase};",
         """ reg [15:0] write_envelope;
 reg [1:0] write_stage;
 always @(posedge clk)begin
  write_envelope<=next_envelope;
  write_stage<=next_stage;
 end
 wire [159:0] next_voice_state={7'd0,harmonics,write_stage,noise[31:14],next_noise,write_envelope,gen,next_phase};"""),
    ])
    change("build.tcl", [("set_option -place_option 1", "set_option -place_option 3")])
    change("rtl/build_identity.vh", [("20261108", "20261112")])
    manifest.update(build_id=0x20261112, parent=str(source), source_sha256=hashes)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
