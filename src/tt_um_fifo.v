/*
 * Copyright (c) 2026 Shlomo Abrams
 * SPDX-License-Identifier: Apache-2.0
 */

// Tiny Tapeout User Module (tt_um) - Top Wrapper for Asynchronous Dual-Clock FIFO (24-pin socket)

//   - ui_in   : 8 inputs
//   - uo_out  : 8 outputs
//   - uio     : 8 bidirectional I/Os (input, output, and output-enable)
//   - "u" prefix      : User signal (ui = User Input, uo = User Output, uio = User I/O)


`default_nettype none // Disables implicit wire creation. Catches typos at compile-time instead of creating silent ASIC bugs!

module tt_um_shlomo_fifo (
    input  wire [7:0] ui_in,    // Dedicated user inputs:  Connected directly to wdata[7:0]
    output wire [7:0] uo_out,   // Dedicated user outputs: Connected directly to rdata[7:0]
    input  wire [7:0] uio_in,   // User I/O(Bidirectional): Input path from pad cells
    output wire [7:0] uio_out,  // User I/O(Bidirectional): Output path to pad cells
    output wire [7:0] uio_oe,   // User I/O(Bidirectional): Output Enable (1 = Output driver active, 0 = Input / Hi-Z)
    input  wire       ena,      // Chip enable (high when this specific project tile is selected on the chip)
    input  wire       clk,      // Default system clock pin (unused here because FIFO is dual-clock)
    input  wire       rst_n     // Global hardware reset (active-low)
);

    // 1. Pin Mapping Strategy:
    // ui_in[7:0]   : Write Data  (wdata[7:0])
    // uo_out[7:0]  : Read Data   (rdata[7:0])
    // Bidirectional IOs (PMOD JC / RPi Pins):
    // uio[0] (in)  : winc   (Write Increment / Enable from external tester)
    // uio[1] (in)  : rinc   (Read Increment / Enable from external tester)
    // uio[2] (in)  : wrst_n (Write Domain Reset, active-low)
    // uio[3] (in)  : rrst_n (Read Domain Reset, active-low)
    // uio[4] (in)  : wclk   (Write Clock from RPi / external oscillator)
    // uio[5] (in)  : rclk   (Read Clock from RPi / external oscillator)
    // uio[6] (out) : wfull  (FIFO Full flag to external tester & LED)
    // uio[7] (out) : rempty (FIFO Empty flag to external tester & LED)

    // 2. Physical Tri-State Pad Direction Control (uio_oe)
    // In physical silicon, each bidirectional pad has a tri-state output driver. uio_oe physically gates that driver:
    // 1 = Drive output out to physical pin, 0 = Turn driver off into High-Impedance (Hi-Z) mode to safely accept inputs
    
    assign uio_oe = 8'b1100_0000;

    // 3. Control Signal Unpacking & Active-Low Reset Logic (De Morgan's Law)
    wire winc   = uio_in[0];
    wire rinc   = uio_in[1];

    // Active-Low Reset: '0' = Reset active, '1' = Normal operation.
    // By De Morgan's Law (not(A) or not(B) == not(A and B)), an AND gate on active-low
    // signals acts as an OR gate:
    //   - If EITHER global rst_n is pulled low (0) OR domain reset uio_in[2]/[3] is low (0),
    //     the internal reset goes low (0) and resets the domain immediately!
    wire wrst_i = rst_n & uio_in[2];
    wire rrst_i = rst_n & uio_in[3];

    wire wclk_i = uio_in[4]; // Write clock routed into tile; CTS builds balanced buffer tree
    wire rclk_i = uio_in[5]; // Read clock routed into tile; CTS builds balanced buffer tree

    wire wfull_o;
    wire rempty_o;

    // 3. Drive Bidirectional Output Pins - Pins 6 & 7 output the status flags; all unused output drivers are tied to 0.
    assign uio_out[0] = 1'b0;
    assign uio_out[1] = 1'b0;
    assign uio_out[2] = 1'b0;
    assign uio_out[3] = 1'b0;
    assign uio_out[4] = 1'b0;
    assign uio_out[5] = 1'b0;
    assign uio_out[6] = wfull_o;
    assign uio_out[7] = rempty_o;

    // 4. Suppress Unused Input Lint Warnings - Because this is an asynchronous dual-clock design, it uses wclk_i and rclk_i
    // rather than the single default 'clk'. ASIC linters (OpenLane / Verilator) flag unused top ports. This reduction-AND satisfies the linter cleanly.
    wire _unused = &{ena, clk, 1'b0};

    // 5. Instantiate Core Parameterized Asynchronous Dual-Clock FIFO
    fifo #(
        .DATA_WIDTH(8),
        .ADDR_WIDTH(4)
    ) u_fifo (
        // Write Domain
        .wclk   (wclk_i),
        .wrst_n (wrst_i),
        .winc   (winc),
        .wfull  (wfull_o),
        .wdata  (ui_in),    
        // Read Domain
        .rclk   (rclk_i),
        .rrst_n (rrst_i),
        .rinc   (rinc),
        .rempty (rempty_o),
        .rdata  (uo_out)   
    );

endmodule
