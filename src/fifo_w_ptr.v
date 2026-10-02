/*
 * Copyright (c) 2026 Shlomo Abrams
 * SPDX-License-Identifier: Apache-2.0
 */

// Write Pointer (Binary & Gray) & Full Flag

`timescale 1ns / 1ps

module fifo_w_ptr #(parameter ADDR_WIDTH = 4)
(
    input  wire                  wclk,
    input  wire                  wrst_n,
    input  wire                  winc,
    input  wire [ADDR_WIDTH:0]   w2q_rptr,   // Synchronized read pointer (Gray)
    output reg                   wfull,
    output wire [ADDR_WIDTH-1:0] waddr,      // Address to memory
    output reg  [ADDR_WIDTH:0]   wptr_g      // Gray pointer to synchronizer
);

    // Current state registers
    reg [ADDR_WIDTH:0] wptr_b_cur;

    // Next-state wires
    wire [ADDR_WIDTH:0] wptr_b_next;
    wire [ADDR_WIDTH:0] wptr_g_next;
    wire                wfull_next;

    // Memory address is binary pointer excluding the extra MSB
    assign waddr = wptr_b_cur[ADDR_WIDTH-1:0];

    // Increment binary pointer only if write enable is asserted and FIFO is not full
    assign wptr_b_next = (winc && !wfull) ? (wptr_b_cur + 1'b1) : wptr_b_cur; // (condition) ? (value_if_true) : (value_if_false), which synthesizes to a 2-to-1 MUX

    // Binary to Gray conversion: G = B ^ (B >> 1)
    assign wptr_g_next = wptr_b_next ^ (wptr_b_next >> 1);

    // Full check: FIFO is full when top 2 Gray bits are inverted, and lower bits match
    assign wfull_next = (wptr_g_next[ADDR_WIDTH]   != w2q_rptr[ADDR_WIDTH]) &&
                        (wptr_g_next[ADDR_WIDTH-1] != w2q_rptr[ADDR_WIDTH-1]) &&
                        (wptr_g_next[ADDR_WIDTH-2:0] == w2q_rptr[ADDR_WIDTH-2:0]);

    // Sequential update on wclk with asynchronous active-low reset
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wptr_b_cur <= {(ADDR_WIDTH+1){1'b0}};
            wptr_g     <= {(ADDR_WIDTH+1){1'b0}};
            wfull      <= 1'b0;
        end else begin
            wptr_b_cur <= wptr_b_next;
            wptr_g     <= wptr_g_next;
            wfull      <= wfull_next;
        end
    end

endmodule
