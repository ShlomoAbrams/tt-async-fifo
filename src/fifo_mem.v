/*
 * Copyright (c) 2026 Shlomo Abrams
 * SPDX-License-Identifier: Apache-2.0
 */

// FIFO Dual-Port RAM Memory Supports independent write/read clocks.

`timescale 1ns / 1ps

module fifo_mem #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4)
(
    // Write Interface
    input  wire                  wclk,
    input  wire                  wclken,
    input  wire [ADDR_WIDTH-1:0] waddr,
    input  wire [DATA_WIDTH-1:0] wdata,
    // Read Interface
    input  wire                  rclk,
    input  wire                  rclken,
    input  wire [ADDR_WIDTH-1:0] raddr,
    output reg  [DATA_WIDTH-1:0] rdata
);

    localparam DEPTH = 1 << ADDR_WIDTH; // Depth = 2^ADDR_WIDTH

    // Memory array storage
    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // Synchronous Write Process
    always @(posedge wclk) begin
        if (wclken) begin // Write if enable is high
            mem[waddr] <= wdata; // Write to Memory 
        end
    end

    // Synchronous Read Process
    always @(posedge rclk) begin
        if (rclken) begin // Read if enable is high
            rdata <= mem[raddr]; // Read from Memory
        end
    end

endmodule
