/*
 * Copyright (c) 2026 Shlomo Abrams
 * SPDX-License-Identifier: Apache-2.0
 */

// Top-Level Asynchronous FIFO - Connects Memory, Pointers & Synchronizers
// Parameterized DATA_WIDTH & ADDR_WIDTH

`timescale 1ns / 1ps

module fifo #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4)
(
    // Write Domain
    input  wire                  wclk,
    input  wire                  wrst_n,
    input  wire                  winc,
    output wire                  wfull,
    input  wire [DATA_WIDTH-1:0] wdata,

    // Read Domain
    input  wire                  rclk,
    input  wire                  rrst_n,
    input  wire                  rinc,
    output wire                  rempty,
    output wire [DATA_WIDTH-1:0] rdata
);

    // Internal interconnection wires
    wire                  wfull_wire;
    wire                  rempty_wire;
    wire                  wclken_wire;
    wire                  rclken_wire;
    wire [ADDR_WIDTH-1:0] waddr_wire;
    wire [ADDR_WIDTH-1:0] raddr_wire;
    wire [ADDR_WIDTH:0]   wptr_wire;    // Write Gray pointer before sync
    wire [ADDR_WIDTH:0]   rptr_wire;    // Read Gray pointer before sync
    wire [ADDR_WIDTH:0]   w2q_rptr;     // Read Gray pointer synchronized to wclk
    wire [ADDR_WIDTH:0]   r2q_wptr;     // Write Gray pointer synchronized to rclk

    // Output assignments
    assign wfull  = wfull_wire;
    assign rempty = rempty_wire;

    // Clock enables (gated by Full/Empty flags to prevent overflow/underflow)
    assign wclken_wire = winc & ~wfull_wire;
    assign rclken_wire = rinc & ~rempty_wire;

    // 1. Dual-Port Storage Memory
    fifo_mem #(.DATA_WIDTH(DATA_WIDTH),.ADDR_WIDTH(ADDR_WIDTH)) 
    fifo_mem_unit (
        .wclk   (wclk),
        .wclken (wclken_wire),
        .waddr  (waddr_wire),
        .wdata  (wdata),
        .rclk   (rclk),
        .rclken (rclken_wire),
        .raddr  (raddr_wire),
        .rdata  (rdata)
    );

    // 2. Write Pointer and Full Flag Logic (wclk domain)
    fifo_w_ptr #(.ADDR_WIDTH(ADDR_WIDTH)) 
    wptr_full_unit (
        .wclk     (wclk),
        .wrst_n   (wrst_n),
        .winc     (winc),
        .w2q_rptr (w2q_rptr),
        .wfull    (wfull_wire),
        .waddr    (waddr_wire),
        .wptr_g   (wptr_wire)
    );

    // 3. Read Pointer and Empty Flag Logic (rclk domain)
    fifo_r_ptr #(.ADDR_WIDTH(ADDR_WIDTH)) 
    rptr_empty_unit (
        .rclk     (rclk),
        .rrst_n   (rrst_n),
        .rinc     (rinc),
        .r2q_wptr (r2q_wptr),
        .rempty   (rempty_wire),
        .raddr    (raddr_wire),
        .rptr_g   (rptr_wire)
    );

    // 4. Write Pointer Synchronizer: Synchronizes wptr_wire into rclk domain
    fifo_synchronizer #(.ADDR_WIDTH(ADDR_WIDTH)) 
    write_to_read_sync (
        .clk     (rclk),
        .rst_n   (rrst_n),
        .ptr_g   (wptr_wire),
        .q2ptr_g (r2q_wptr)
    );

    // 5. Read Pointer Synchronizer: Synchronizes rptr_wire into wclk domain
    fifo_synchronizer #(.ADDR_WIDTH(ADDR_WIDTH)) 
    read_to_write_sync (
        .clk     (wclk),
        .rst_n   (wrst_n),
        .ptr_g   (rptr_wire),
        .q2ptr_g (w2q_rptr)
    );

endmodule
