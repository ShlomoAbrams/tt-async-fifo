/*
 * Copyright (c) 2026 Shlomo Abrams
 * SPDX-License-Identifier: Apache-2.0
 */

// Read Pointer (Binary & Gray) & Empty Flag

`timescale 1ns / 1ps

module fifo_r_ptr #(parameter ADDR_WIDTH = 4)
(
    input  wire                  rclk,
    input  wire                  rrst_n,
    input  wire                  rinc,
    input  wire [ADDR_WIDTH:0]   r2q_wptr,   // Synchronized write pointer (Gray)
    output reg                   rempty,
    output wire [ADDR_WIDTH-1:0] raddr,      // Address to memory
    output reg  [ADDR_WIDTH:0]   rptr_g      // Gray pointer to synchronizer
);

    // Current state registers
    reg [ADDR_WIDTH:0] rptr_b_cur;

    // Next-state wires
    wire [ADDR_WIDTH:0] rptr_b_next;
    wire [ADDR_WIDTH:0] rptr_g_next;
    wire                rempty_next;

    // Memory address is binary pointer excluding the extra MSB
    assign raddr = rptr_b_cur[ADDR_WIDTH-1:0];

    // Increment binary pointer only if read enable is asserted and FIFO is not empty
    assign rptr_b_next = (rinc && !rempty) ? (rptr_b_cur + 1'b1) : rptr_b_cur; // (condition) ? (value_if_true) : (value_if_false), which synthesizes to a 2-to-1 MUX

    // Binary to Gray conversion: G = B xor (B >> 1)
    assign rptr_g_next = rptr_b_next ^ (rptr_b_next >> 1);

    // Empty flag: raise flag when next read Gray pointer equals synchronized write Gray pointer
    assign rempty_next = (rptr_g_next == r2q_wptr);

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin  // Async reset: clear Flip-Flops
            rptr_b_cur <= {(ADDR_WIDTH+1){1'b0}};
            rptr_g     <= {(ADDR_WIDTH+1){1'b0}};
            rempty     <= 1'b1;  // FIFO is empty on reset
        end else begin      // update Flip-Flops to next value
            rptr_b_cur <= rptr_b_next;
            rptr_g     <= rptr_g_next;
            rempty     <= rempty_next;
        end
    end

endmodule
