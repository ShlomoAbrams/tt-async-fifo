<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

An Asynchronous Dual-Clock First-In First-Out (FIFO) buffer designed to safely transfer 8-bit data between two completely independent, unsynchronized clock domains (CDC).

### Architecture Highlights
1. **Dual-Clock Domains:** Independent `wclk` (write clock) and `rclk` (read clock).
2. **2-Stage D Flip-Flop Synchronizers:** Converts binary write and read pointers to Gray code prior to domain crossing, guaranteeing only a single bit toggles per step to prevent metastability hazards.
3. **Precise Flag Generation:** `wfull` is asserted in the write domain; `rempty` is asserted in the read domain.
4. **Capacity:** Depth of 16 bytes, data width of 8 bits.
5. **Overflow / Underflow Protection:** Memory writes are gated when full, and memory reads are gated when empty to prevent corrupted state.

## How to test

1. Assert active-low resets (`rst_n=0`, `wrst_n=0`, `rrst_n=0`) while toggling `wclk` and `rclk`.
2. Verify initial flags: `rempty=1` and `wfull=0`.
3. Drive 8-bit data onto `ui_in[7:0]`, assert write increment `winc=1` (`uio[0]=1`), and pulse write clock `wclk` (`uio[4]`).
4. Observe that `rempty` deasserts to 0.
5. Write 16 consecutive bytes until `wfull=1` (`uio[6]=1`).
6. Read bytes back out by asserting read increment `rinc=1` (`uio[1]=1`) and pulsing read clock `rclk` (`uio[5]`).
7. Verify all 16 bytes emerge on `uo_out[7:0]` in exact first-in, first-out order.

## External hardware

Raspberry Pi, Digilent Basys 3 FPGA, or microcontroller for dual-clock generation and I/O bus driving.
